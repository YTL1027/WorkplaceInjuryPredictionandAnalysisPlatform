import datetime

from django.db import models
from django.utils import timezone


class PredictionTask(models.Model):
    note = models.TextField(max_length=200, default="")
    prediction_type = models.CharField(max_length=100)
    naics_level = models.IntegerField(default=2)
    start_date = models.DateField(null=False, default=datetime.date.min)
    end_date = models.DateField(null=False, default=datetime.date.max)
    process_time = models.DateTimeField(default=timezone.now)
    finish_time = models.DateTimeField(null=True)
    status = models.CharField(max_length=100, default="")
    log = models.TextField(default="")
    progress = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    model = models.TextField(max_length=50, default="")
    naics = models.TextField(max_length=10000, default="")
    county = models.TextField(max_length=10000, default="")
    severity = models.TextField(max_length=10000, default="")
    evaluation = models.CharField(max_length=1000, default="")

    def __str__(self):
        return f"{self.id}"


class CommonwealthSummary(models.Model):
    mean = models.DecimalField(max_digits=10, decimal_places=7)
    std = models.DecimalField(max_digits=10, decimal_places=7)
    percentile_25 = models.DecimalField(max_digits=10, decimal_places=7)
    percentile_50 = models.DecimalField(max_digits=10, decimal_places=7)
    percentile_75 = models.DecimalField(max_digits=10, decimal_places=7)
    high_ir_month = models.CharField(max_length=15, null=True)
    avg_time = models.DurationField()
    summary_time = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.id}"


class NonCommonwealthSummary(models.Model):
    mean = models.DecimalField(max_digits=10, decimal_places=7)
    std = models.DecimalField(max_digits=10, decimal_places=7)
    percentile_25 = models.DecimalField(max_digits=10, decimal_places=7)
    percentile_50 = models.DecimalField(max_digits=10, decimal_places=7)
    percentile_75 = models.DecimalField(max_digits=10, decimal_places=7)
    high_ir_month = models.CharField(max_length=15, null=True)
    avg_time = models.DurationField()
    summary_time = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.id}"


class PredictionOutput(models.Model):
    naics_code = models.CharField(max_length=200)
    county = models.CharField(max_length=50)
    severity = models.CharField(max_length=50)
    year = models.IntegerField()
    month = models.IntegerField()
    month_str = models.CharField(max_length=15)
    claim_number = models.IntegerField()
    emp_count = models.IntegerField()
    injury_rate = models.FloatField(null=True)
    type = models.CharField(max_length=15)
    naics_level = models.IntegerField()
    commonwealth = models.PositiveSmallIntegerField()
    county_formatted = models.CharField(max_length=55)
    task = models.ForeignKey(PredictionTask, on_delete=models.CASCADE)
    date = models.DateField(null=True)

    def __str__(self):
        return f"{self.id}"
