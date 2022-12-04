"""
Description: This file defines some data processing methods for medical costs data.
@author CMU Capstone, Fall 2022
"""
from django.conf import settings
import pandas as pd

class ETLMedicalCost(object):
    
    def __init__(self, data: pd.DataFrame(), task_id: int, logger):
        """
        Constructor to initialize instance of ETLMedicalCost. 
        
        Arguments:
        - data = Raw data from the medical costs file
        - task_id = Upload task id
        - logger = Logger object
        """
        self.data = data            
        self.task_id = task_id      
        self.logger = logger        

    def preprocess(self):
        """
        Processes and the medical costs data by checking, filtering, and renaming columns. 
        """
        # Check the columns needed are included in the file
        self.logger.message("Checking column names.")
        self.check_columns()
        # Only keep necessary columns
        self.logger.message("Filtering data columns.")
        self.filter_columns()
        # Reordering and renaming columns
        self.logger.message("Reordering and renaming columns.")
        self.fix_columns()

        return self.data

    def check_columns(self): 
        """
        Checks to see if the columns needed to build the clean dataframe are included in the uploaded file.
        """
        for col in settings.MEDICAL_COST_COLS:
            if not col in self.data.columns:
                raise Exception(f"Column '{col}' not found in the data file. Please ensure the column names are in the first row and spelled correctly.")

    def filter_columns(self):
        """
        Filters out unnecessary columns. 
        """
        self.data = self.data.loc[:, settings.MEDICAL_COST_COLS]

    def fix_columns(self):
        """
        With the remianing columns, reorders and renames columns to match the database table. 
        """
        # Fill missing values with 0
        self.data["Claim Numeric"] = self.data["Claim Numeric"].fillna(0)
        self.data["WCAIS Claim Number"] = self.data["WCAIS Claim Number"].fillna(0)
        self.data["PartOfBody"] = self.data["PartOfBody"].fillna(0)
        self.data["Confidence"] = self.data["Confidence"].fillna(0)

        # Create clean dataframe 
        data_clean = pd.DataFrame()
        data_clean["pcrb_claim_number"] = self.data["Claim Numeric"].astype(int)
        data_clean["wcais_claim_number"] = self.data["WCAIS Claim Number"].astype(int)
        data_clean["accident_date"] = pd.to_datetime(self.data["Accident Date"])
        data_clean["part_of_body"] = self.data["PartOfBody"].astype(int)
        data_clean["injury_cause_id"] = self.data["CauseOfInjury"].astype(int)
        data_clean["injury_nature_id"] = self.data["NatureOfInjury"].astype(int)
        data_clean["amount_charged"] = self.data["Amount Charged"]
        data_clean["amount_paid"] = self.data["Amount Paid"]
        data_clean["confidence"] = self.data["Confidence"].astype(int)

        self.data = data_clean

