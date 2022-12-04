import pandas as pd
from preprocess_module import models
from django.core.management.base import BaseCommand
from django.conf import settings
import os

injury_cause = "Cause_of_Injury_Mapping.csv"
naics_lookup = "NAICS_Lookup.csv"
injury_nature = "Nature_of_Injury_Mapping.csv"
zip_county = "zip_county.csv"


class Command(BaseCommand):
    help = "Initializes the database with the lookup information."

    def handle(self, *args, **kwargs):
        self.stdout.write(f"Loading injury cause mapping from file: {injury_cause}")
        df = pd.read_csv(
            os.path.join(settings.BASE_DIR, "..", "Data", injury_cause),
            names=["injury_code", "description", "category", "score"],
            header=0,
        )
        models.InjuryCause.objects.bulk_create(
            models.InjuryCause(**vals) for vals in df.to_dict("records")
        )

        self.stdout.write(f"Loading NAICS lookup mapping from file: {naics_lookup}")
        df = pd.read_csv(
            os.path.join(settings.BASE_DIR, "..", "Data", naics_lookup),
            names=["naics", "description"],
            header=0,
        )
        models.NAICS.objects.bulk_create(
            models.NAICS(**vals) for vals in df.to_dict("records")
        )

        self.stdout.write(f"Loading injury nature mapping from file: {injury_nature}")
        df = pd.read_csv(
            os.path.join(settings.BASE_DIR, "..", "Data", injury_nature),
            names=["injury_code", "description", "category", "score"],
            header=0,
        )
        models.InjuryNature.objects.bulk_create(
            models.InjuryNature(**vals) for vals in df.to_dict("records")
        )

        self.stdout.write(f"Loading injury cause mapping from file: {zip_county}")
        df = pd.read_csv(
            os.path.join(settings.BASE_DIR, "..", "Data", zip_county),
            names=["zipcode", "county"],
        )
        # Add blank code
        df = df.append({"zipcode": 999999, "county": "Out Of State"}, ignore_index=True)
        models.ZipCounty.objects.bulk_create(
            models.ZipCounty(**vals) for vals in df.to_dict("records")
        )
