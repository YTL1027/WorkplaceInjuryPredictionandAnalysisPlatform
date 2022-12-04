from django.db import models
from django.utils import timezone


class UploadTask(models.Model):
    file_name = models.CharField(max_length=100, null=False, unique=True)
    file = models.FileField()
    file_type = models.CharField(max_length=100)
    status = models.CharField(max_length=100, default="")
    log = models.TextField(default="")
    upload_time = models.DateTimeField(default=timezone.now)
    progress = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.file_name}"


class InjuryCause(models.Model):
    injury_code = models.IntegerField(primary_key=True, null=False)
    description = models.CharField(max_length=500, default=None)
    category = models.CharField(max_length=100, default=None)
    score = models.FloatField(default=0)

    def __str__(self):
        return f"{self.injury_code}"


class ZipCounty(models.Model):
    zipcode = models.IntegerField(primary_key=True, null=False)
    county = models.CharField(max_length=100, default=None)

    def __str__(self):
        return f"{self.zipcode}"


class InjuryNature(models.Model):
    injury_code = models.IntegerField(primary_key=True, null=False)
    description = models.CharField(max_length=500, default=None)
    category = models.CharField(max_length=100, default=None)
    score = models.FloatField(default=0)

    def __str__(self):
        return f"{self.injury_code}"


class NAICS(models.Model):
    naics = models.CharField(max_length=100)
    description = models.CharField(max_length=500, default=None)

    def __str__(self):
        return f"{self.naics}"


class Claim(models.Model):
    claim_number = models.IntegerField(null=False)
    naics = models.CharField(max_length=30, null=False)
    county = models.CharField(max_length=100, default=None)
    severity = models.CharField(max_length=30, default=None)
    claim_date = models.DateField()
    source = models.ForeignKey(UploadTask, on_delete=models.CASCADE)
    injury_code = models.ForeignKey(InjuryCause, on_delete=models.DO_NOTHING)
    zip_code = models.ForeignKey(ZipCounty, on_delete=models.DO_NOTHING)
    type = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.claim_number}"


class Employment(models.Model):
    naics_str = models.CharField(max_length=50, null=False)
    county = models.CharField(max_length=100, null=False)
    year = models.IntegerField()
    quarter = models.IntegerField()
    month1 = models.IntegerField()
    month2 = models.IntegerField()
    month3 = models.IntegerField()
    source = models.ForeignKey(UploadTask, on_delete=models.CASCADE) 

    def __str__(self):
        return f"{self.id}"


class MedicalCost(models.Model):
    pcrb_claim_number = models.IntegerField(null=False)       
    wcais_claim_number = models.IntegerField(null=True)     # WCAIS claim number, joins with Claim model
    accident_date = models.DateField(default=None)
    part_of_body = models.IntegerField(null=True)
    injury_cause_id = models.IntegerField(null=True)        
    injury_nature_id = models.IntegerField(null=True)
    amount_charged = models.DecimalField(max_digits=16, decimal_places=2, default=None)
    amount_paid = models.DecimalField(max_digits=16, decimal_places=2, default=None)
    confidence = models.IntegerField(null=True)

    def __str__(self):
        return f"{self.id}"

