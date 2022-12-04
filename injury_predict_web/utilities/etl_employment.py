"""
Description: This file defines some data processing methods for employment data.
Author: CMU Capstone Team 2019Fall
"""
from django.conf import settings
import pandas as pd

class ETLEmployment(object):
    """docstring for ETLEmployment.
    This is a class for preprocessing employment data files"""

    def __init__(self,data,task_id,logger):
        self.data = data
        self.task_id = task_id
        self.logger = logger

    def check_columns(self):
        for col in settings.EMPLOYMENT_COLS:
            if not col in self.data.columns:
                raise Exception(f"Column '{col}' not found in the data file. Please ensure the column names are in the first row and spelled correctly.")
    
    def preprocess(self):
        # ensure the correct columns are provied
        self.logger.message("Checking column names.")
        self.check_columns()
        # only keep necessary data
        self.logger.message("Filtering data columns.")
        self.filter_columns()
        # clean data
        self.logger.message("Cleaning data.")
        self.clean_df()

        return self.data

    def filter_columns(self):
        # Keep only needed columns
        self.data = self.data.loc[:, settings.EMPLOYMENT_COLS]

    def clean_df(self):
        self.data["source_id"] = self.task_id
        self.data.columns = [
            "year",
            "quarter",
            "county",
            "naics_str",
            "month1",
            "month2",
            "month3",
            "source_id",
        ]
        # CHECK IF OK
        self.data["month1"] = self.data["month1"].fillna(0).astype(int)
        self.data["month2"] = self.data["month2"].fillna(0).astype(int)
        self.data["month3"] = self.data["month3"].fillna(0).astype(int)
