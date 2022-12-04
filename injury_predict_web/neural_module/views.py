from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
import logging
import pandas as pd
from .predict_injury_nature import InjuryNaturePrediction
from injury_predict_web.settings import REPORT_ID


class NeuralSiteView(LoginRequiredMixin, View):
    def get(self, request):
        logging.info("Preprocess view visited")
        return render(
            request,
            "preprocess_module/neural.html",
            {
                "report_id": REPORT_ID
            }
        )


class NeuralView(viewsets.ViewSet):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated]
    injury_prediction_model = InjuryNaturePrediction()

    def convert_dataframe(self, file):
        """
        Convert django inmemoryfile to dataframe
        :param file
        :return
        """
        temporary_path = file.temporary_file_path()
        df_data = None
        if temporary_path.endswith("xlsx"):
            df_data = pd.read_excel(temporary_path)
        else:
            df_data = pd.read_csv(temporary_path)
        return df_data

    def calculate_freq(self, freq):
        freq_map = {}
        for i in range(len(freq)):
            nature_list = freq[i][19].split(",")
            for nature in nature_list:
                if nature not in freq_map.keys():
                    freq_map[nature] = 0
                freq_map[nature] = freq_map[nature] + 1
        return freq_map

    def create(self, request):
        """
        POST request. create new preprocess task.
        :param request:
        :return:
        """
        
        file = request.FILES["file"]
        df = self.convert_dataframe(file)

        # predict
        predict = self.injury_prediction_model.neural_predict(df)
        freq_map = self.calculate_freq(predict)
        data = {
            "report_id": REPORT_ID,
            "prediction": predict,
            "freq_map": freq_map
        }

        return Response(data)
