import datetime
import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views import View
from rest_framework import viewsets, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from preprocess_module import models
from injury_predict_web.settings import REPORT_ID
from preprocess_module.serializer import UploadTaskSerializer
import preprocess_module.tasks as tasks
from utilities.etl_controller import ETLController
from utilities.logger import Logger
import logging

#############################
########## Views ############
#############################


class PreprocessSiteView(LoginRequiredMixin, View):
    queryset = models.UploadTask.objects
    serializer_class = UploadTaskSerializer
    parser_classes = (MultiPartParser, FormParser)
    login_url = "/admin/login/"
    redirect_field_name = "next"

    def get(self, request):
        logging.info("Preprocess view visited")
        serializer = self.serializer_class(
            self.queryset.all().order_by("-upload_time"), many=True
        )
        data = json.loads(json.dumps(serializer.data))

        return render(
            request,
            "preprocess_module/upload.html",
            {"data": data, "report_id": REPORT_ID},
        )


class HelpView(LoginRequiredMixin, View):
    login_url = "/admin/login/"
    redirect_field_name = "next"

    def get(self, request):
        logging.info("Help view visited")
        return render(request, "preprocess_module/help.html")


#############################
########### APIs ############
#############################
class PreprocessView(viewsets.ViewSet):
    queryset = models.UploadTask.objects
    serializer_class = UploadTaskSerializer
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """
        GET request. List upload tasks ordered by upload time
        :param request:
        :return:
        """
        serializer = self.serializer_class(
            self.queryset.all().order_by("-upload_time"), many=True
        )
        return Response(serializer.data)

    def create(self, request):
        """
        POST request. create new preprocess task.
        :param request:
        :return:
        """
        file = request.FILES["file"]
        file_name = file.name

        data = request.data
        data["status"] = "Uploading..."
        data["log"] = "[{}]  Uploading the file....".format(
            timezone.localtime(timezone.now()).strftime("%X")
        )
        data["file_name"] = file_name.split(".")[0]

        serializer = self.serializer_class(data=data)
        if serializer.is_valid(raise_exception=True):
            task_obj = serializer.save()
            if serializer.data["file_type"] == "Employment":
                tasks.preprocess_employment(task_obj.id)
            elif serializer.data["file_type"] == "MedicalCost":
                tasks.preprocess_medical_costs(task_obj.id)
            # Else, process as Claims
            else:
                tasks.preprocess_claims(task_obj.id)

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_404_NOT_FOUND)

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

    def destroy(self, request, pk=None):
        """
        Destroy upload task as well as uploaded data.
        :param request:
        :param pk:
        :return:
        """
        task = get_object_or_404(self.queryset.all(), pk=pk)
        task.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class SummaryView(viewsets.ViewSet):
    def list(self, request):
        """
        GET request. retrieve basic statics for the data.
        :param request:
        :return:
        """
        emp_count = models.Employment.objects.all().count()
        cw_count = models.Claim.objects.filter(type="Commonwealth").count()
        non_cw_count = models.Claim.objects.filter(type="Non-Commonwealth").count()
        data = {
            "emp_count": emp_count,
            "cw_count": cw_count,
            "non_cw_count": non_cw_count,
        }
        return Response(data)
