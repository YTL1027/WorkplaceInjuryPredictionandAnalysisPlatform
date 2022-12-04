from django.contrib import admin
from preprocess_module.models import *
from django.apps import apps


app = apps.get_app_config("preprocess_module")

for model_name, model in app.models.items():
    admin.site.register(model)
