from django.contrib import admin

from prediction_module.models import *
from django.apps import apps


app = apps.get_app_config("prediction_module")

for model_name, model in app.models.items():
    admin.site.register(model)
