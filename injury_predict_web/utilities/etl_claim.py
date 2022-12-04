"""
Description: this file defines the methods to preprocess claims data.
Filter columns, map cause scores to get severity,

Author: CMU Capstone Team 2019Fall
Modified by: CMU Capstone Team 2021Fall
Comment by: CMU Capstone Team 2020Fall (Cindy)
"""
from django.conf import settings
import logging
import math
import pandas as pd
from preprocess_module import models
import pickle
import os


class ETLClaim(object):
    """docstring for ClaimGroup.
    This is an instance of an group of claims that will be forcasted on.
    Each group is identified by the NAICS code, county, and severity count data for a particular county and NAICS code."""

    def __init__(self,data,task_id,file_type,logger):
        self.cause = pd.DataFrame(list(models.InjuryCause.objects.all().values()))
        self.nature = pd.DataFrame(list(models.InjuryNature.objects.all().values()))
        self.pa_zip_county = pd.DataFrame(list(models.ZipCounty.objects.all().values()))
        self.data = data
        self.zip_cols = [
            "EMPLR_PHY_POSTAL_CD",
            "EMPL_MLNG_POSTAL_CD",
        ]
        self.task_id = task_id
        self.file_type = file_type
        self.logger = logger

    def check_columns(self):
        for col in settings.CLAIM_COLS:
            if not col in self.data.columns:
                raise Exception(f"Column '{col}' not found in the data file. Please ensure the column names are in the first row and spelled correctly.")
    
    def filter_columns(self):
        """
        This method defines the WCAIS file columns header that is needed to be identified by the etl process.
        :return:
        """
        self.data = self.data.loc[:, settings.CLAIM_COLS]

    def fix_zips(self):
        """
        Ensures each zip is a 5 digit code
        :return:
        """
        # iterate through each column of zip codes
        for col in self.zip_cols:
            # Fill all the missing values with a space
            self.data.loc[:, col].fillna(" ", inplace=True)
            # fix each zip code
            self.data[col] = self.data[col].apply(self.fix_zip)

            if self.zip_cols[0] == col:  # check to see if this is the first iteration
                self.data.loc[:, "zip_code"] = None  # add a new column for final zip codes

            self.data.loc[:, "zip_code"].fillna(
                self.data.loc[:, col], inplace=True
            )  # add final zip codes

        # delete initial zip code columns
        self.data.drop(self.zip_cols, axis=1, inplace=True)

    def fix_zip(self, zip_code):
        """
        zip_code is a single zip code.
        :param zip_code:
        :return:
        """
        zip_code = str(zip_code)  # make sure zip code is a string
        if (
            zip_code[:1] == " "
        ):  # zip code does not exist or there is an error with the zip code. Return None
            return None
        else:
            return zip_code[:5]  # return only the first 5 digits of the zip code

    def zip_to_county(self):
        # change zipcode to string
        self.pa_zip_county.loc[:, "zipcode"] = self.pa_zip_county["zipcode"].apply(str)
        label = self.data.columns[5]
        # left join dataframe by zipcode
        self.data = pd.merge(
            self.data, self.pa_zip_county, how="left", left_on=label, right_on="zipcode"
        )
        # fill out county as out of state
        self.data.loc[self.data["county"].isnull(), "county"] = "Out Of State"
        # fill out zipcode as dummy zipcode
        self.data.loc[self.data["zipcode"].isnull(), "zipcode"] = 999999
        self.data = self.data.drop([label], axis=1)

    def fix_naics(self):
        self.data.loc[:, "NAICS"] = [
            str(int(x)) if not math.isnan(x) else "999999" for x in self.data.loc[:, "NAICS"]
        ]

    def impute_medical_costs(self):
        """
        Adds medical costs to self.data dataframe to be used in severity assignment. 
        Imputes claims with no medical costs with median values. 
        """
        # Get medical costs
        medical_costs = pd.DataFrame(list(models.MedicalCost.objects.all().values()))

        # Drop any claims with non-matching INJURY_CAUSE_CD
        self.data = self.data.merge(self.cause, left_on="INJURY_CAUSE_CD", right_on="injury_code")
        self.data = self.data.drop(["injury_code", "description", "category", "score"], axis=1)

        # Merge with medical costs
        self.data = self.data.merge(medical_costs[['wcais_claim_number', 'amount_paid']], left_on='CLAIM_NUMBER', right_on='wcais_claim_number', how='left')
        self.data = self.data.drop(['wcais_claim_number'], axis=1)

        # Merge all current claims and medical costs
        filename = os.path.join(settings.BASE_DIR, "..", "Data", "median_medical_costs.csv")
        median_costs = pd.read_csv(filename) 

        # Convert data to integer
        median_costs['NAICS'] = median_costs['NAICS'].astype(int)
        median_costs['INJURY_CAUSE_CD'] = median_costs['INJURY_CAUSE_CD'].astype(int)
        median_costs['INJURY_NATURE_CD'] = median_costs['INJURY_NATURE_CD'].astype(int)
        median_costs['median_amount_paid'] = median_costs['median_amount_paid'].astype(float)
        self.data['NAICS'] = self.data['NAICS'].astype(int)
        self.data['INJURY_CAUSE_CD'] = self.data['INJURY_CAUSE_CD'].astype(int)
        self.data['INJURY_NATURE_CD'] = self.data['INJURY_NATURE_CD'].astype(int)
        
        # Assign median values to new claim data
        self.data = self.data.merge(median_costs, left_on=['NAICS', 'INJURY_CAUSE_CD', 'INJURY_NATURE_CD'], right_on=['NAICS', 'INJURY_CAUSE_CD', 'INJURY_NATURE_CD'], how='left')
        
        # Use median if not matching real amount_paid
        self.data['amount_paid'] = self.data['amount_paid'].combine_first(self.data['median_amount_paid'])

        # Fill missing day with median 
        self.data['amount_paid'] = self.data['amount_paid'].fillna(self.data['amount_paid'].median())

        # Drop unnecessary columns
        self.data = self.data.drop(['INJURY_NATURE_CD', 'median_amount_paid'], axis=1)

    def get_severity(self):
        """
        Assigns severity using stored jenks natural breaks algorithm. 
        Jenks trained and split on part median medical costs by injury cause code and nature code. 
        """
        # Load jenks natural breaks model 
        filename = os.path.join(settings.BASE_DIR, "..", "Data", "breaks.sav") 
        model = pickle.load(open(filename, 'rb'))

        # Run on unpickled model
        self.data['severity'] = pd.cut(self.data['amount_paid'], bins=model, labels=['Low', 'Medium', 'High'], include_lowest=True)

        # Fill remaining values with "High severity"
        self.data['severity'] = self.data['severity'].fillna('High')

        # Drop amount_paid column
        self.data = self.data.drop(["amount_paid"], axis=1)

    def fix_datetime(self):
        self.data["date"] = pd.to_datetime(self.data["DT_OF_INJURY"])
        self.data.drop("DT_OF_INJURY", axis=1, inplace=True)

    def preprocess(self):
        # ensure correct columns are proviced
        self.logger.message("Checking column names.")
        self.check_columns()
        # only keep necessary data
        self.logger.message("Filtering data columns.")
        self.filter_columns()
        # fix zip codes
        self.logger.message("Cleaning zipcodes.")
        self.fix_zips()
        # map zipcode to county
        self.logger.message("Mapping zipcodes to counties.")
        self.zip_to_county()
        # Fix NAICS codes
        self.logger.message("Cleaning NAICS codes.")
        self.fix_naics()
        # Impute medical costs
        self.logger.message("Imputting medical costs")
        self.impute_medical_costs()
        # Get Severity
        self.logger.message("Calculating severity scores.")
        self.get_severity()
        # Split out date
        self.logger.message("Extracting date information.")
        self.fix_datetime()
        # finalize
        self.logger.message("Adding file info.")
        self.data["source_id"] = self.task_id
        self.data["type"] = self.file_type
        self.logger.message("Cleaning up data structure.")
        self.logger.message(self.data.head())
        self.data.columns = [
            "naics",
            "claim_number",
            "injury_code_id",
            "zip_code_id",
            "county",
            "severity",
            "claim_date",
            "source_id",
            "type",
        ]
        self.logger.message(self.data.head())
        self.logger.message("1")
        self.data["injury_code_id"] = self.data["injury_code_id"].astype(int)
        self.logger.message("1")
        self.data["zip_code_id"] = self.data["zip_code_id"].astype(int)
        self.logger.message("1")
        return self.data
