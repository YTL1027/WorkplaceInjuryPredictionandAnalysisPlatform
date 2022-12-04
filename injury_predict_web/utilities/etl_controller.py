"""
Description: ETLController class defines the whole process of preprocess data, which serves as the ETL controller.
Read file, preprocess claims data, preprocess employment data.

Author: CMU Capstone Team 2019Fall
Comment by: CMU Capstone Team 2020Fall (Cindy)
"""

from django.conf import settings
import pandas as pd
from pyxlsb import open_workbook
from preprocess_module import models
from utilities import etl_employment
from utilities.etl_claim import ETLClaim
from utilities.etl_employment import ETLEmployment
from utilities.etl_medical_cost import ETLMedicalCost
from utilities.logger import Logger


class ETLController:
    def __init__(self, task):
        self.task = task
        self.logger = Logger(task)

    @staticmethod
    def read_file(path):
        """
        This function read file to dataframe
        :param path: file path
        :return: dataframe
        """
        suffix = path[path.rfind(".") + 1 :]
        if suffix == "xlsx":  # Read Excel File
            return pd.read_excel(path)
        elif suffix == "xlsb":  # Read xlsb File
            doc = []
            with open_workbook(path) as wb:
                for sheetname in wb.sheets:
                    with wb.get_sheet(sheetname) as sheet:
                        for row in sheet.rows():
                            values = [r.v for r in row]  # retrieving content
                            doc.append(values)
            return pd.DataFrame(doc[1:], columns=doc[0])
        elif suffix == "csv":  # Read CSV File
            return pd.read_csv(path)

    def preprocess_claims(self):
        """
        load and save claim data to db
        :return:
        """
        try:
            # load the data
            self.logger.message("Reading claims data...")
            data = self.read_file(self.task.file.path)
            
            # clean the data
            self.logger.message("Cleaning claims data...")
            etl_claim = ETLClaim(data,self.task.id,self.task.file_type,self.logger)
            clean_df = etl_claim.preprocess()

            # save the data to db
            self.logger.message("Loading claims data to database...")
            models.Claim.objects.bulk_create(
                models.Claim(**vals) for vals in clean_df.to_dict("records")
            )

            # finalize
            self.logger.message("Successfully load claims data into database...")
            self.task.status = "Successful"
            self.task.save()

        # error occurred
        except Exception as e:
            self.task.status = "Error"
            self.logger.message(e)
            self.task.save()

    def preprocess_employment(self):
        """
        load and save employment data to db
        :return:
        """
        try:
            # load the data
            self.logger.message("Reading employment data...")
            data = self.read_file(self.task.file.path)
            
            # clean the data
            self.logger.message("Cleaning employment data...")
            etl_employment = ETLEmployment(data,self.task.id,self.logger)
            clean_df = etl_employment.preprocess()

            # save the data to db
            self.logger.message("Loading employment data to database...")
            models.Employment.objects.bulk_create(
                models.Employment(**vals) for vals in clean_df.to_dict("records")
            )

            # finalize
            self.logger.message("Successfully load employment data into database.")
            self.task.status = "Successful"
            self.task.save()

        # error occurred
        except Exception as e:
            self.logger.message(e)
            self.task.status = "Error"
            self.task.save()

    def preprocess_medical_costs(self):
        """
        Load and save medical costs data to database.
        """
        try:
            # load the data
            self.logger.message("Reading medical cost data...")
            data = self.read_file(self.task.file.path)
            
            # clean the data
            self.logger.message("Cleaning medical cost data...")
            etl_medical_cost = ETLMedicalCost(data,self.task.id,self.logger)
            clean_df = etl_medical_cost.preprocess()

            # save the data to db
            self.logger.message("Loading medical cost data to database...")
            models.MedicalCost.objects.bulk_create(
                models.MedicalCost(**vals) for vals in clean_df.to_dict("records")
            )

            # finalize
            self.logger.message("Successfully load medical cost data into database.")
            self.task.status = "Successful"
            self.task.save()

        # error occurred
        except Exception as e:
            self.logger.message(e)
            self.task.status = "Error"
            self.task.save()


