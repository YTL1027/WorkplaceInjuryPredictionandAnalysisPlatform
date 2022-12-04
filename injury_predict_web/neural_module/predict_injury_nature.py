from sched import scheduler
from statistics import mode
import pandas as pd
import numpy as np
import json
from pip import main
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import torchvision
import torchvision.transforms as transforms
import os

from .embedding_model import EmbeddingModel
from joblib import load
from sklearn.preprocessing import OrdinalEncoder
from background_task import background
from django.conf import settings


"""
Args:
        model_path:
            The path of the weights of the model
        onehot_path:
            The path of the one-hot encoder, which is used to transform the softmax output to the injury nature code
        ordinal_paths:
            The paths of the ordinal encoders, which is used to transform original features (X) to ordinal features
"""

PROJECT_ROOT = settings.PROJECT_ROOT

model_path = os.path.join(PROJECT_ROOT, "nn_model/model5.pt") 
onehot_path = os.path.join(PROJECT_ROOT, "nn_model/onehot.joblib")
ordinal_paths = [os.path.join(PROJECT_ROOT, "nn_model/ordinal0.joblib"), os.path.join(PROJECT_ROOT, "nn_model/ordinal1.joblib"), os.path.join(PROJECT_ROOT,"nn_model/ordinal2.joblib"), os.path.join(PROJECT_ROOT, "nn_model/ordinal3.joblib")]

init = False

class InjuryNaturePrediction():
    """Class used to predict injury natures

    Methods:
        Constructor: Load models and encoders
        predict: predict injury natures based on loaded model and encoders

    """

    def __init__(self):
        """Constructor. Load models and encoders from specific paths
        """
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = EmbeddingModel([(1053, 100), (64, 100), (69, 100), (4, 100)], 1)
        self.model.load_state_dict(torch.load(model_path, map_location='cpu'))
        self.required_fields = ["2012 NAICS", "EMPLR_PHY_STATE_CD", "EMPL_MLNG_STATE_CD", "GENDER_TYPE_CD", "BIRTHDT", "year"]
        self.encoders = [load(path) for path in ordinal_paths]
        self.onehot_encoder = load(onehot_path) 


    def __getstate__(self):
        state = self.__dict__.copy()
        del state["model"]
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.model = torch.load(model_path, map_location='cpu')

    def predict(self, wcais_data):
        """Predict injury natures based on loaded model and encoders

        Args:
        wcais_data
            dataframe stores the sample to predict

        Returns:
        valid_row:
            data that used to predict
        y_pred:
            the prediction result in injury nature codes
        """
        X_raw, valid_row = self.parse_excel(wcais_data)

        X = self.get_feature(X_raw)
        X_cat, X_con = torch.Tensor(X[:, :-1]).to(self.device), torch.Tensor(X[:, -1].reshape(-1, 1)).to(self.device)
        X_cat = X_cat.type(torch.cuda.IntTensor if torch.cuda.is_available() else torch.LongTensor)

        outputs = self.model(X_cat, X_con)
        y_pred = self.decode_outputs(outputs.cpu().detach().numpy())
        
        
        return valid_row, y_pred


    def parse_excel(self, wcais_data):
        dataset = []
        valid_row = []
        max_num = 10000
        cnt = 0
        for i in range(wcais_data.shape[0]):
            if cnt == max_num:
                break
            cnt += 1

            row = wcais_data.loc[i]
            
            # check data integrety
            if not self.check_row(row):
                continue
            
            # store original row into the list
            valid_row.append(list(row))

            # parse data point
            datapoint = []
            for field in self.required_fields:
                datapoint.append(row[field])
                
            year = datapoint[-1]
            birth_year = datapoint[4].year
            age = year - birth_year
            
            datapoint[4] = age
            datapoint = datapoint[:-1]
            
            dataset.append(datapoint)

        return np.array(dataset), np.array(valid_row)


    def check_row(self, row):
        for field in self.required_fields:
            if str(row[field.strip()]).lower() in {"nan", "nat"}:
                return False
        return True

    def get_feature(self, X_raw):
        naics = X_raw[:, 0].reshape(-1, 1)
        emplr_loc = X_raw[:, 1].reshape(-1, 1)
        empl_loc = X_raw[:, 2].reshape(-1, 1)
        gender = X_raw[:, 3].reshape(-1, 1)
        age = X_raw[:, 4].reshape(-1, 1).astype("int32")

        naics_encoded = self.encoders[0].transform(naics)
        emplr_loc_encoded = self.encoders[1].transform(emplr_loc)
        empl_loc_encoded = self.encoders[2].transform(empl_loc)
        gender_encoded = self.encoders[3].transform(gender)

        X = np.concatenate((naics_encoded, emplr_loc_encoded, empl_loc_encoded, gender_encoded, age), axis=1)
        X = X.astype("int32")

        return X


    def decode_outputs(self, outputs):
        y_pred = []

        for row in outputs:
            indices = np.argsort(row)
            indices = indices[-5:]
            onehots = []
            for index in indices:
                onehot = [0 for i in range(55)]
                onehot[index] = 1
                onehots.append(onehot)
            natures = self.onehot_encoder.inverse_transform(onehots)
            y_pred.append(natures)
        
        y_pred = np.array(y_pred)
        return y_pred


    def neural_predict(self, wcais_data):
        prediction_process = InjuryNaturePrediction()
        x, y = prediction_process.predict(wcais_data)
        rs = [[""] * 20 for i in range(len(x))]
        for i in range(len(x)):
            top_5_nature = ""
            for j in range(len(x[i])):
                try:
                    if np.isnan(x[i][j]):
                        rs[i][j] = "-"
                    else:
                        rs[i][j] = str(x[i][j])
                except:
                    rs[i][j] = str(x[i][j])
            for j in range(5):
               top_5_nature += str(y[j][0][0]) + ","
            rs[i][19] = top_5_nature[:-1]
        return rs
