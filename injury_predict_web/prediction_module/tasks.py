from background_task import background
from prediction_module.models import PredictionTask
from utilities.logger import Logger
from utilities.predict_controller import ProphetPrediction, SARIMAXPrediction
from django.shortcuts import get_object_or_404


@background(schedule=1)
def predict(task_id):
    task = get_object_or_404(PredictionTask.objects, pk=task_id)

    if (task.model == "Prophet"):
        prediction = ProphetPrediction(task)
    elif (task.model == "SARIMAX"):
        prediction = SARIMAXPrediction(task)
    else:
        # no prediction model found
        pass
    
    prediction.run()
