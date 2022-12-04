from background_task import background
from preprocess_module.models import UploadTask
from utilities.logger import Logger
from django.shortcuts import get_object_or_404
from utilities.etl_controller import ETLController


# load and preprocess employment data file
@background(schedule=1)
def preprocess_employment(task_id):
    task = get_object_or_404(UploadTask.objects, pk=task_id)
    etl_controller = ETLController(task)
    task.status = "Processing..."
    task.save()
    etl_controller.preprocess_employment()

# load and preprocess claim data file
@background(schedule=1)
def preprocess_claims(task_id):
    task = get_object_or_404(UploadTask.objects, pk=task_id)
    etl_controller = ETLController(task)
    task.status = "Processing..."
    task.save()
    etl_controller.preprocess_claims()

# load and preprocess medial cost data file
@background(schedule=1)
def preprocess_medical_costs(task_id):
    task = get_object_or_404(UploadTask.objects, pk=task_id)
    etl_controller = ETLController(task)
    task.status = "Processing..."
    task.save()
    etl_controller.preprocess_medical_costs()
