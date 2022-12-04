import json
import math

import pandas as pd
import numpy as np
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.db.models.functions import ExtractYear, ExtractWeek
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views import View
from rest_framework import viewsets, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from injury_predict_web.settings import REPORT_ID
from prediction_module.models import (
    PredictionTask,
    CommonwealthSummary,
    NonCommonwealthSummary,
)
from prediction_module.serializer import PredictionTaskSerializer
from preprocess_module.models import ZipCounty, NAICS
from utilities.logger import Logger
import prediction_module.tasks as tasks
import logging
from django.http import FileResponse, Http404


#############################
########## Views ############
#############################
class PredictionSiteView(LoginRequiredMixin, View):
    queryset = PredictionTask.objects
    serializer_class = PredictionTaskSerializer
    parser_classes = (MultiPartParser, FormParser)
    login_url = "/admin/login/"
    redirect_field_name = "next"
    counties = ZipCounty.objects
    naics = NAICS.objects

    def get(self, request):
        # Get Prediction tasks
        serializer = self.serializer_class(
            self.queryset.all().order_by("-process_time"), many=True
        )
        task_data = json.loads(json.dumps(serializer.data))

        # Get list of counties
        county_data = json.loads(
            json.dumps(
                list(
                    self.counties.all()
                    .order_by("county")
                    .values_list("county", flat=True)
                    .distinct()
                )
            )
        )

        # Get list of naics codes
        naics_df = pd.DataFrame(
            list(self.naics.all().values_list("naics", "description")),
            columns=["naics_code", "description"],
            dtype="str",
        )
        naics_df["length"] = naics_df["naics_code"].str.len()
        naics_data = {}
        for level in naics_df["length"].unique().tolist():
            naics_data[level] = naics_df.loc[
                naics_df["length"] == level, ["naics_code", "description"]
            ].values.tolist()
        naics_data = json.loads(json.dumps(naics_data))

        return render(
            request,
            "prediction_module/prediction.html",
            {
                "task_data": task_data,
                "report_id": REPORT_ID,
                "county_data": county_data,
                "naics_data": naics_data,
            },
        )


class StatsView(LoginRequiredMixin, View):
    login_url = "/admin/login/"
    redirect_field_name = "next"

    def get(self, request):
        return render(request, "prediction_module/stats.html", {"report_id": REPORT_ID})


class ReportView(LoginRequiredMixin, View):
    login_url = "/admin/login/"
    redirect_field_name = "next"

    def get(self, request):
        return render(
            request, "prediction_module/report.html", {"report_id": REPORT_ID}
        )


#############################
########### APIs ############
#############################
class PredictionView(viewsets.ViewSet):
    queryset = PredictionTask.objects
    serializer_class = PredictionTaskSerializer
    parser_classes = (MultiPartParser, FormParser)

    def list(self, request):
        serializer = self.serializer_class(
            self.queryset.all().order_by("-process_time"), many=True
        )
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """
        Retreive details of particular upload task
        :param request:
        :param pk:
        :return:
        """
        task = get_object_or_404(self.queryset.all(), pk=pk)
        serializer = self.serializer_class(task)
        return Response(serializer.data)

    def create(self, request):
        data = request.data.copy()
        data["status"] = "In Process"
        data["log"] = "[{}]  Initiating...".format(
            timezone.localtime(timezone.now()).strftime("%X")
        )
        serializer = self.serializer_class(data=data)

        if serializer.is_valid(raise_exception=True):

            task_obj = serializer.save()
            logging.info("Task object:  " + str(task_obj.id))
            tasks.predict(task_obj.id)

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_404_NOT_FOUND)

    def destroy(self, request, pk=None):
        """
        Destroy prediction task as well as data in prediction_output table.
        Other prediction table records (prediction summary) will not be deleted.
        :param request:
        :param pk:
        :return:
        """
        task = get_object_or_404(self.queryset.all(), pk=pk)
        task.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PredictionSummaryView(viewsets.ViewSet):
    queryset = PredictionTask.objects
    serializer_class = PredictionTaskSerializer
    parser_classes = (MultiPartParser, FormParser)

    def list(self, request):
        """
        GET request. retrieve basic statics for the data.
        :param request:
        :return:
        """
        # sql_proxy = SQLProxy()
        # sql_proxy.connect()
        # prediction_time = sql_proxy.read_from_sql(PREDICTION_PROCESS_TIME)
        # REPLACE WITH
        prediction_time = pd.DataFrame(
            list(self.queryset.values_list("process_time", "finish_time")),
            columns=["process_time", "finish_time"],
        )
        prediction_time.process_time = pd.to_datetime(prediction_time.process_time)
        prediction_time.finish_time = pd.to_datetime(prediction_time.finish_time)
        prediction_time = prediction_time.dropna()

        prediction_time["time_used"] = (
            prediction_time["finish_time"] - prediction_time["process_time"]
        )
        avg_time = prediction_time["time_used"].mean()
        logging.info("process_time, finish_time")
        logging.info(prediction_time.head())
        if pd.Timedelta("nan") == avg_time or (
            isinstance(avg_time, float) and math.isnan(avg_time)
        ):
            avg_time = 0
        logging.info("avg_time = " + str(avg_time))

        cw_count = len(PredictionTask.objects.filter(prediction_type="Commonwealth"))
        non_cw_count = len(
            PredictionTask.objects.filter(prediction_type="Non-Commonwealth")
        )

        cw_summary = CommonwealthSummary.objects.all().order_by("-id")
        cw_time = 0
        cw_mean = 0
        cw_std = 0
        cw_75 = 0
        cw_high_month = ""
        ncw_summary = NonCommonwealthSummary.objects.all().order_by("-id")
        ncw_time = 0
        ncw_mean = 0
        ncw_std = 0
        ncw_75 = 0
        ncw_high_month = ""
        if len(cw_summary) > 0:
            cw_summary = cw_summary[0]
            cw_time = cw_summary.avg_time
            cw_mean = cw_summary.mean
            cw_std = cw_summary.std
            cw_75 = cw_summary.percentile_75
            cw_high_month = cw_summary.high_ir_month
        if len(ncw_summary) > 0:
            ncw_summary = ncw_summary[0]
            ncw_time = ncw_summary.avg_time
            ncw_mean = ncw_summary.mean
            ncw_std = ncw_summary.std
            ncw_75 = ncw_summary.percentile_75
            ncw_high_month = ncw_summary.high_ir_month

        data = {
            "cw_count": cw_count,
            "non_cw_count": non_cw_count,
            "avg_time": avg_time,
            "cw_avg_time": cw_time,
            "cw_mean": cw_mean,
            "cw_std": cw_std,
            "cw_75_pct": cw_75,
            "cw_high_ir_month": cw_high_month,
            "ncw_avg_time": ncw_time,
            "ncw_mean": ncw_mean,
            "ncw_std": ncw_std,
            "ncw_75_pct": ncw_75,
            "ncw_high_ir_month": ncw_high_month,
        }

        return Response(data)


def get_evaluation_file(request, id):
    """
    get evaluation file for each task
    :param request: http request
    :param id: task id
    :return: evaluation pdf file
    """
    prediction_task = get_object_or_404(PredictionTask, id=id)
    evaluation_path = prediction_task.evaluation

    if len(evaluation_path) == 0:
        raise Http404("Evaluation Not Completed, Please try later")
    try:
        return FileResponse(open(evaluation_path, 'rb'), content_type='application/pdf')
    except FileNotFoundError as e:
        raise Http404("Evaluation File Not Exist, Please check if prediction success")
