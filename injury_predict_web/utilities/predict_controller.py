import pandas as pd
import numpy as np
from django.conf import settings
from django.utils import timezone
from django.db.models import Avg
from prediction_module import models as prediction_models
from preprocess_module import models as preprocess_models
import logging
from injury_predict_web.settings import OUTPUT_PATH
from statsmodels.tsa.statespace import sarimax
from utilities.logger import Logger

import statsmodels.api as sm
from statsmodels.tsa.statespace import sarimax
from statsmodels.tools.eval_measures import rmse

import matplotlib.pyplot as plt

from matplotlib.backends.backend_pdf import PdfPages

import json
from fbprophet import Prophet
from fbprophet.serialize import model_to_json, model_from_json
from fbprophet.diagnostics import cross_validation
from fbprophet.diagnostics import performance_metrics
from fbprophet.plot import plot_cross_validation_metric


class Prediction:
    def __init__(self, task):
        self.task = task
        self.is_commonwealth = task.prediction_type == "Commonwealth"
        self.logger = Logger(task)
        self.claim_df = None
        self.emp_df = None
        self.actual = None
        self.forecast = None
        self.latest_emp = None
        self.prediction_output = None
        self.county_filter = task.county.split(";")
        self.naics_filter = task.naics.split(";")
        self.progress = 0

    def updateProgress(self, value):
        self.progress += value
        self.task.progress = self.progress
        self.task.save()

    def run(self):
        """
        Run prediction pipeline. load data from database, create claim group,
        process employment data, do prediction, load output back to database.
        :return:
        """
        try:
            # First retrieve the data from the database
            self.logger.message("Retrieving data...")
            self.load_data()
            self.logger.message("Data retrieved from database.")
            self.updateProgress(1)

            # Aggregate the claims into groups
            self.logger.message("Creating claim groups...")
            self.aggregate_claims()
            self.logger.message("Claim groups created.")
            self.updateProgress(1)

            # Clean up the employment data
            self.logger.message("Processing employment data...")
            self.process_emp_data()
            self.logger.message("Employment data processed.")
            self.updateProgress(1)

            # Merge the claim and employment data
            self.logger.message("Merging claim and employment data...")
            self.merge_claims_emp()
            self.logger.message("Finished merging claim and employment data.")
            self.updateProgress(1)

            # Calculate the historical injury rates
            self.logger.message("Calculating injury rates...")
            self.calc_injury_rate()
            self.logger.message("Finished calculating injury rates.")
            self.updateProgress(1)

            # Run forecasts
            self.logger.message("Forecasting injury rates")
            self.forecast_injury_rates()
            self.logger.message("Finished forecasting injury rates.")

            # Prediction and Evaluate
            self.logger.message("Predicting and evaluating results")
            file_path = 'sarimax.model'
            data_path = 'observed.data'
            attribute_name = 'y'
            pdf_path = "{}evaluation_{}.pdf".format(OUTPUT_PATH, self.task.id)
            self.evaluate(file_path, data_path, attribute_name, pdf_path)
            self.task.evaluation = pdf_path
            self.logger.message("Finished predicting and evaluating results.")

            # Predict claims with forecasted injury rates
            self.logger.message("Forecasting claim counts...")
            self.forecast_claims()
            self.logger.message("Finished forecasting claims.")
            self.updateProgress(2)

            # Prepare prediction output
            self.logger.message("Preparing final predictions...")
            self.prepare_prediction_output()
            self.logger.message("Finished preparing prediction output.")
            self.updateProgress(1)

            # Save output
            self.logger.message("Load prediction output to database...")
            self.prediction_output.to_csv(
                "{}output_{}.csv".format(OUTPUT_PATH, self.task.id)
            )
            self.load_output_to_db()
            self.logger.message("Successful load to database.")

            # Update task status and save
            self.task.status = "Successful"
            self.task.finish_time = timezone.localtime(timezone.now())
            self.task.progress = 100
            self.task.save()

            # Generate output summary
            self.logger.message("Generating summary...")
            self.generate_summary()
            self.logger.message("Summary Updated.")

            self.logger.message("Prediction complete.")

        except Exception as e:
            self.task.status = "Error"
            self.task.finish_time = timezone.localtime(timezone.now())
            self.task.progress = 100
            self.logger.message(e)
            self.task.save()

    def evaluate(self, model_path, data_path, attribute_name, pdf_path):
        """
        load the model previously saved, start to evaluate the model, finally save the results into one pdf document.
        """

        if self.task.model == 'SARIMAX':
            results = sarimax.SARIMAXResultsWrapper.load(model_path)
            y_observed = pd.read_csv(data_path)[attribute_name]

            def residual_diagnostics(r=results):
                fig = r.plot_diagnostics(figsize=(16, 8))
                pdf.savefig(fig)

            def evaluate_with_ci(r=results, y=y_observed):
                predict = r.get_prediction(dynamic=False)
                predict_ci = predict.conf_int(0.01)

                # Graph
                fig, ax = plt.subplots(figsize=(16, 8))
                ax.set(title='Evaluation & Confidence Interval',
                       xlabel='Time', ylabel='Injury Rate')

                # Plot data points
                y.plot(ax=ax, style='o', label='Observed')

                # Plot predictions
                pred = predict.predicted_mean
                pred.reset_index(drop=True, inplace=True)
                pred.plot(ax=ax, style='r--', label='Predict')
                predict_ci.reset_index(drop=True, inplace=True)
                ax.fill_between(predict_ci.index,
                                predict_ci.iloc[:, 0],
                                predict_ci.iloc[:, 1], color='k', alpha=.1)

                bonds = [min(y) * 0.6, max(y) * 1.1]
                plt.ylim(bonds)
                plt.legend()
                pdf.savefig(fig)

            def predict_with_ci(years=5, r=results, y=y_observed):
                # Graph
                fig, ax = plt.subplots(figsize=(16, 8))
                ax.set(title='Prediction & Confidence Interval',
                       xlabel='Time', ylabel='Injury Rate')
                pred_uc = r.get_forecast(steps=12 * years)
                pred_ci = pred_uc.conf_int()
                ax = y.plot(label='observed')

                pred_uc.predicted_mean.plot(ax=ax, style='r--', label='Forecast')
                ax.fill_between(pred_ci.index,
                                pred_ci.iloc[:, 0],
                                pred_ci.iloc[:, 1], color='k', alpha=.2)

                ax.set_xlabel('Time')
                ax.set_ylabel('Injury rate')
                bonds = [min(y) * 0.1, max(y) * 1.8]
                plt.ylim(bonds)
                plt.legend()
                pdf.savefig(fig)

            with PdfPages(pdf_path) as pdf:
                try:
                    evaluate_with_ci()
                    predict_with_ci()
                    residual_diagnostics()

                    d = pdf.infodict()
                    d['Title'] = 'Evaluation Report'
                    d.close()
                except:
                    print("error")

        else:
            with open('serialized_model.json', 'r') as fin:
                m = model_from_json(json.load(fin))  # Load model

            with PdfPages(pdf_path) as pdf:
                years = 5
                future = m.make_future_dataframe(periods=365 * years)
                future.tail()

                forecast = m.predict(future)
                forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail()

                df_cv = cross_validation(m, initial='0 days', period='180 days', horizon='730 days')

                try:
                    fig1 = m.plot(forecast)
                    fig1.set_size_inches(16, 8)
                    pdf.savefig(fig1)

                    fig2 = m.plot_components(forecast)
                    fig2.set_size_inches(16, 8)
                    pdf.savefig(fig2)

                    fig3 = plot_cross_validation_metric(df_cv, metric='rmse')
                    fig3.set_size_inches(16, 8)
                    pdf.savefig(fig3)

                    fig4 = plot_cross_validation_metric(df_cv, metric='mape')
                    fig4.set_size_inches(16, 8)
                    pdf.savefig(fig4)
                    d = pdf.infodict()
                    d['Title'] = 'Evaluation Report'
                except:
                    print("error")

    def load_data(self):
        """
        load claim data and employment data from database to a dataframe
        """
        # Get claims data based on defined filter from task
        self.claim_df = pd.DataFrame(
            list(
                preprocess_models.Claim.objects.filter(
                    type=self.task.prediction_type,
                    claim_date__gte=self.task.start_date,
                    claim_date__lte=self.task.end_date,
                    county__in=self.county_filter,
                ).values()
            )
        )
        # Make sure there is data
        if (len(self.claim_df) == 0):
            raise Exception('No claim records found that meet the criteria.')

        # convert naics code to specified level
        self.claim_df["naics"] = self.claim_df["naics"].apply(self.process_naics)
        # filter out naics codes
        self.claim_df = self.claim_df[self.claim_df.naics.isin(self.naics_filter)]

        # Log number of claim records
        self.logger.message(f"{len(self.claim_df)} claim records loaded.")

        # Get employment data based on defined filter from task
        self.emp_df = pd.DataFrame(
            list(
                preprocess_models.Employment.objects.filter(
                    year__gte=self.task.start_date.year,
                    year__lte=self.task.end_date.year,
                    naics_str__in=self.naics_filter,
                ).values_list(
                    "naics_str",
                    "county",
                    "year",
                    "quarter",
                    "month1",
                    "month2",
                    "month3",
                )
            ),
            columns=[
                "naics",
                "county",
                "year",
                "quarter",
                "1",
                "2",
                "3",
            ],
        )
        # Make sure there is data
        if (len(self.emp_df) == 0):
            raise Exception('No employment records found that meet the criteria.')
        # Log number of employment records
        self.logger.message(f"{len(self.emp_df)} employment records loaded.")

    def process_naics(self, value):
        """
        Function to process the naics code
        Takes full naics code and truncates it to the specified level
        :return: string of naics code
        """
        # truncate code to specified level
        naics_code = value[: self.task.naics_level]

        # if level 2 is specified -- need to make groupings
        if self.task.naics_level == 2:
            if naics_code in settings.GROUPED_NAICS:
                naics_code = settings.GROUPED_NAICS[naics_code]

        # return the code
        return naics_code

    def aggregate_claims(self):
        """
        Aggregate claim counts by:
            NAICS
            County
            Year
            Month
        :return:
        """
        # extract year and month from date and reset date to first day of month
        self.claim_df["year"] = pd.DatetimeIndex(self.claim_df["claim_date"]).year
        self.claim_df["month"] = pd.DatetimeIndex(self.claim_df["claim_date"]).month
        self.claim_df["day"] = 1
        self.claim_df["date"] = pd.to_datetime(self.claim_df[["year", "month", "day"]])
        del self.claim_df["day"]  # only need day to calculate date

        # aggregate claim counts for each severity
        self.claim_df = (
            self.claim_df.groupby(
                ["naics", "county", "year", "month", "date", "severity"],
                as_index=False,
            )
                .agg({"id": "count"})
                .rename(columns={"id": "claim_count"})
        )

        # aggregate all claim counts
        all_claims = (
            self.claim_df.groupby(
                ["naics", "county", "year", "month", "date"],
                as_index=False,
            )
                .agg({"claim_count": "sum"})
        )
        all_claims["severity"] = "All"

        # append to claim_df
        self.claim_df = self.claim_df.append(
            all_claims[["naics", "county", "year", "month", "date", "severity", "claim_count"]])

        # Log # of groups created
        self.logger.message(f"{len(self.claim_df)} claim groups created.")

    def process_emp_data(self):
        """
        Process and transform employment data for easier prediction
        :return:
        """
        # melt the dataframe so that monthly counts are in each row
        self.emp_df = pd.melt(
            self.emp_df,
            id_vars=[
                "naics",
                "county",
                "year",
                "quarter",
            ],
            var_name="month",
            value_name="emp_count",
        )
        # calculate correct month since the month is based on
        # number of months in quarter q
        # e.g. month # = (quarter-1) * 3 + month
        self.emp_df["month"] = (self.emp_df["quarter"] - 1) * 3 + self.emp_df[
            "month"
        ].astype(int)

        # convert to generic date of the first day of each month
        self.emp_df["day"] = 1
        self.emp_df["date"] = pd.to_datetime(self.emp_df[["year", "month", "day"]])

        # clean up unused columns
        del self.emp_df["day"]
        del self.emp_df["quarter"]

        # Log number of employment records
        self.logger.message(
            f"Employment data broken out into {len(self.emp_df)} records."
        )

    def merge_claims_emp(self):
        """
        Merge aggregate claim counts with employment counts
        :return:
        """
        # only merge employment records for naics/county pairs found in the claim data
        # e.g. if there have never been any claim counts for a naics/county then don't forecast them
        mask = (self.emp_df["naics"] + self.emp_df["county"]).isin(
            (self.claim_df["naics"] + self.claim_df["county"])
        )

        # Instantiate actual dataframe
        self.actual = pd.DataFrame()
        severity_values = self.task.severity.split(",")

        # Iterate through severity types to get with employee count and fill in missing values
        for s in severity_values:
            s_dataframe = self.claim_df[self.claim_df["severity"] == s].merge(
                self.emp_df.loc[mask],
                how="outer",
                on=["naics", "county", "year", "month", "date"],
            )

            # Fill missing values with 0
            s_dataframe["claim_count"].fillna(0, inplace=True)
            s_dataframe["emp_count"].fillna(0, inplace=True)
            s_dataframe["severity"].fillna(s, inplace=True)

            # Append severity claims to actual dataframe
            if(self.actual.empty):
                self.actual = s_dataframe
            else:
                self.actual = self.actual.append(s_dataframe)

        # Log merged data length
        self.logger.message(
            f"Merged claim and employment into {len(self.actual)} records."
        )

    def calc_injury_rate(self):
        """
        Calculate the injury rate as # claims / # employees
        :return:
        """
        self.actual["injury_rate"] = (
                self.actual.loc[:, "claim_count"] / self.actual.loc[:, "emp_count"]
        )

        # Replace infinity and null values with 0
        self.actual["injury_rate"].replace([np.inf, -np.inf, np.nan], 0, inplace=True)

    def predict(self, id, df):
        """
        Method to predict injury rates for a given group.
        Should be overriden by children classes.
        """
        return None

    def forecast_injury_rates(self):
        """
        Iterate over all the groups and forecast the injury rates
        :return:
        """
        try:
            # Store the forecasts in a list
            data = []

            # Group data into claim groups
            forecast_df = self.actual.groupby(["naics", "county", "severity"])

            # Log # of forecasts
            self.logger.message(f"Running forecasts over {len(forecast_df)} groups.")
            forecast_count = 0
            progress_increment = (1.0 / len(forecast_df)) * 90
            for id, df in forecast_df:  # For each claim group.
                # forecast injury rates
                forecast = self.predict(id, df)
                # append forecasts to list if data is returned
                if len(forecast) > 0:
                    data.extend(forecast.values.tolist())
                    forecast_count += 1
                self.updateProgress(progress_increment)

            # Convert list data to a dataframe
            self.injury_rate_forecasts = pd.DataFrame(
                data,
                columns=[
                    "naics",
                    "county",
                    "severity",
                    "year",
                    "month",
                    "date",
                    "injury_rate_forecast",
                ],
            )

            # Log # of successful forecasts
            self.logger.message(f"Successfully forecasted {forecast_count} groups.")

        except Exception as e:
            self.logger.message(e)

    def forecast_claims(self):
        """
        Use forecasted injury rates to calculate the forecasted claim counts
        Forecasted claim count = forecasted injury rate * latest employment count
        When prediction results in negative or null forecast:
            instead use previous years historical injury rate as future prediction
            if all else fails, then use 0 as prediction
        :return:
        """
        # get latest employment count for each naics/county
        mask = (
                self.emp_df.groupby(["naics", "county"])["date"].transform(max)
                == self.emp_df["date"]
        )
        self.latest_emp = self.emp_df.loc[mask, ["naics", "county", "emp_count"]]

        # merge the forecasted injury rates with the latest employment counts
        self.forecast = self.injury_rate_forecasts.merge(
            self.latest_emp, how="left", on=["naics", "county"]
        )

        # calculate forecasted claim counts as injury rate * employee count
        self.forecast["claim_count"] = (
                self.forecast.loc[:, "injury_rate_forecast"]
                * self.forecast.loc[:, "emp_count"]
        )

        """
        if na or negative use previous years injury rate * latest employee count
        if still na or negative set to 0
        """
        # get date of last year
        self.forecast["prev_date"] = self.forecast.loc[:, "date"] - pd.DateOffset(
            years=1
        )
        # merge actual injury rate for last year
        self.forecast = self.forecast.merge(
            self.actual[["naics", "county", "date", "severity", "injury_rate"]].rename(
                columns={"date": "prev_date"}
            ),
            how="left",
            on=["naics", "county", "prev_date", "severity"],
        )
        del self.forecast["prev_date"]
        # replace na or negative with previous years injury rate * latest employee count
        mask = ~(self.forecast["claim_count"] >= 0)
        self.logger.message(f"{mask.sum()} out of {len(mask)} records are na/negative.")
        self.forecast.loc[mask, "claim_count"] = (
                self.forecast.loc[mask, "injury_rate"]
                * self.forecast.loc[mask, "emp_count"]
        )
        self.forecast.loc[mask, "injury_rate_forecast"] = self.forecast.loc[
            mask, "injury_rate"
        ]
        # if still na or negative replace with 0
        mask = ~(self.forecast["claim_count"] >= 0)
        self.forecast.loc[mask, "claim_count"] = 0

        # set NAs to 0
        self.forecast["injury_rate_forecast"].fillna(0, inplace=True)
        self.forecast["emp_count"].fillna(0, inplace=True)

    def prepare_prediction_output(self):
        """
        Prepare final prediction output
        Combine historical data with forecasted data
        :return:
        """
        # reformat actuals
        self.actual["type"] = "Actual"
        self.actual = self.actual[
            [
                "naics",
                "county",
                "year",
                "month",
                "date",
                "severity",
                "claim_count",
                "emp_count",
                "injury_rate",
                "type",
            ]
        ].rename(columns={"naics": "naics_code", "claim_count": "claim_number"})

        # reformat forecasts
        self.forecast["type"] = "Predicted"
        self.forecast = self.forecast[
            [
                "naics",
                "county",
                "year",
                "month",
                "date",
                "severity",
                "claim_count",
                "emp_count",
                "injury_rate_forecast",
                "type",
            ]
        ].rename(
            columns={
                "naics": "naics_code",
                "claim_count": "claim_number",
                "injury_rate_forecast": "injury_rate",
            }
        )

        # concatenate actual and forecast
        self.prediction_output = pd.concat([self.actual, self.forecast])

        # add additional info
        self.prediction_output["county_formatted"] = (
                self.prediction_output["county"] + " PA"
        )
        self.prediction_output["month_str"] = self.prediction_output[
            "date"
        ].dt.month_name()
        self.prediction_output["naics_level"] = self.task.naics_level
        self.prediction_output["commonwealth"] = self.is_commonwealth
        self.prediction_output["task_id"] = self.task.id

    def load_output_to_db(self):
        """
        load output data to database table, this will be linked to powerBI report
        """
        self.logger.message(
            f"Saving {len(self.prediction_output)} records to the database."
        )
        prediction_models.PredictionOutput.objects.bulk_create(
            prediction_models.PredictionOutput(**vals)
            for vals in self.prediction_output.to_dict("records")
        )

    def generate_summary(self):
        """
        generate summary used for web summary part and the chart,
        store the information into prediction_task table
        note: non-common data is the same as "All industries" on the web interface
        """

        # Get prediction time for commonwealth tasks
        cw_prediction_time = pd.DataFrame(
            list(
                prediction_models.PredictionTask.objects.filter(
                    prediction_type="Commonwealth",
                ).values_list("process_time", "finish_time")
            ),
            columns=["process_time", "finish_time"],
        ).dropna()
        if len(cw_prediction_time) > 0:
            cw_prediction_time["time_used"] = (
                    cw_prediction_time["finish_time"] - cw_prediction_time["process_time"]
            )
            # Calculate average time taken
            cw_avg_time = cw_prediction_time["time_used"].mean()

        # Get prediction time for non-commonwealth tasks
        ncw_prediction_time = pd.DataFrame(
            list(
                prediction_models.PredictionTask.objects.filter(
                    prediction_type="Non-Commonwealth",
                ).values_list("process_time", "finish_time")
            ),
            columns=["process_time", "finish_time"],
        ).dropna()
        if len(ncw_prediction_time) > 0:
            ncw_prediction_time["time_used"] = (
                    ncw_prediction_time["finish_time"] - ncw_prediction_time["process_time"]
            )
            # Calculate average time taken
            ncw_avg_time = ncw_prediction_time["time_used"].mean()

        # Generate Injury Summary for injury rates related statistics
        cw_ir_df = pd.DataFrame(
            prediction_models.PredictionOutput.objects.filter(
                type="Actual",
                commonwealth=True,
            )
                .values("year", "month")
                .annotate(avg_injury_rate=Avg("injury_rate"))
        )
        ncw_ir_df = pd.DataFrame(
            prediction_models.PredictionOutput.objects.filter(
                type="Actual",
                commonwealth=False,
            )
                .values("year", "month")
                .annotate(avg_injury_rate=Avg("injury_rate"))
        )
        # if common wealth data is not empty, calculate stats
        if len(cw_ir_df) > 0:
            # Calculate summary statistics
            cw_details = cw_ir_df["avg_injury_rate"].describe()
            cw_summary = prediction_models.CommonwealthSummary(
                high_ir_month=cw_ir_df["month"].iloc[
                    cw_ir_df["avg_injury_rate"].idxmax()
                ],  # which month has the highest injury among prediction years
                mean=cw_details.loc["mean"],
                std=cw_details.loc["std"],
                percentile_25=cw_details.loc["25%"],
                percentile_50=cw_details.loc["50%"],
                percentile_75=cw_details.loc["75%"],
                avg_time=cw_avg_time,
            )
            cw_summary.save()

        # if noncommon wealth data is not empty, calculate stats
        if len(ncw_ir_df) > 0:
            # Calculate summary statistics
            ncw_details = ncw_ir_df["avg_injury_rate"].describe()
            ncw_summary = prediction_models.CommonwealthSummary(
                high_ir_month=ncw_ir_df["month"].iloc[
                    ncw_ir_df["avg_injury_rate"].idxmax()
                ],  # which month has the highest injury among prediction years
                mean=ncw_details.loc["mean"],
                std=ncw_details.loc["std"],
                percentile_25=ncw_details.loc["25%"],
                percentile_50=ncw_details.loc["50%"],
                percentile_75=ncw_details.loc["75%"],
                avg_time=ncw_avg_time,
            )
            ncw_summary.save()


class ProphetPrediction(Prediction):
    def __init__(self, task):
        Prediction.__init__(self, task)

    def predict(self, id, df):
        """
        Overwrites the prediction method to use the prophet model.
        """
        # only run prediction if we have at least 3 months of data
        if len(df) >= 3:
            # format training data for Prophet model
            train = (
                df.loc[:, ["date", "injury_rate"]]
                    .rename(columns={"date": "ds", "injury_rate": "y"})
                    .sort_values(by="ds")
            )
            # create model
            m = Prophet(yearly_seasonality=True)
            # train
            try:
                # Fit model to historical data
                m.fit(train, iter=250)

                with open('serialized_model.json', 'w') as fout:
                    json.dump(model_to_json(m), fout)  # Save model

                # Create future dataset
                future = m.make_future_dataframe(periods=settings.PREDICTION_STEP, freq="MS")
                # Forecast injury rates
                pred = m.predict(future)

                # Prepare output data
                pred = pred.iloc[-settings.PREDICTION_STEP:]
                pred = pred[["ds", "yhat"]]
                pred["date"] = pd.to_datetime(pred["ds"])
                pred["naics"] = id[0]
                pred["county"] = id[1]
                pred["year"] = pd.DatetimeIndex(pred["date"]).year
                pred["month"] = pd.DatetimeIndex(pred["date"]).month

            except Exception as e:
                print(e)
                return pd.DataFrame()
        else:
            print("Input dataframe length is smaller than 3, return empty dataframe")
            return pd.DataFrame()

        return pred[["naics", "county", "year", "month", "date", "yhat"]]


class SARIMAXPrediction(Prediction):
    def __init__(self, task):
        Prediction.__init__(self, task)

    def predict(self, id, df):
        """
        Overwrites the prediction method to use the SARIMAX model.
        """
        # only run prediction if we have at least 3 months of data
        if len(df) >= 3:
            try:
                # format training data for SARIMAX model
                train = (
                    df.loc[:, ["date", "injury_rate"]]
                        .rename(columns={"date": "ds", "injury_rate": "y"})
                        .sort_values(by="ds")
                )
                train["y"] = train.loc[:, "y"].astype("float")

                # Create model
                model = sarimax.SARIMAX(
                    train["y"],
                    order=(1, 1, 1),
                    seasonal_order=(1, 1, 0, 12),
                    enforce_invertibility=False,
                )

                # Fit model to historical data
                result = model.fit()

                # Save model
                file_path = 'sarimax.model'
                data_path = 'observed.data'
                result.save(file_path)
                train["y"].to_csv(data_path)

                # Forecast injury rates
                forecast = result.get_forecast(steps=settings.PREDICTION_STEP).predicted_mean

                # Prepare output data
                pred = pd.DataFrame(
                    pd.date_range(
                        start=pd.to_datetime(train.iloc[-1, 0])
                              + pd.DateOffset(months=1),
                        periods=settings.PREDICTION_STEP,
                        freq=pd.DateOffset(months=1),
                    ),
                    columns=["ds"],
                )
                pred["yhat"] = forecast.to_numpy()
                pred["date"] = pd.to_datetime(pred["ds"])
                pred["naics"] = id[0]
                pred["county"] = id[1]
                pred["severity"] = id[2]
                pred["year"] = pd.DatetimeIndex(pred["date"]).year
                pred["month"] = pd.DatetimeIndex(pred["date"]).month

            except Exception as e:
                print(e)
                return pd.DataFrame()
        else:
            print("Input dataframe length is smaller than 3, return empty dataframe")
            return pd.DataFrame()

        return pred[["naics", "county", "severity", "year", "month", "date", "yhat"]]
