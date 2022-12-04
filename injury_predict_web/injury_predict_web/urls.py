"""injury_predict_web URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from prediction_module.views import PredictionView, PredictionSummaryView
from preprocess_module.views import PreprocessSiteView, PreprocessView, SummaryView
from neural_module.views import NeuralView

router = DefaultRouter()
router.register(r"preprocess/task", PreprocessView, base_name="preprocess-task")
router.register(r"preprocess/summary", SummaryView, base_name="preprocess-summary")
router.register(r"prediction/task", PredictionView, base_name="prediction-task")
router.register(r"neural/task", NeuralView, base_name="neural-task")
router.register(
    r"prediction/summary", PredictionSummaryView, base_name="prediction-summary"
)

admin.site.site_header = "PA Labor Injury Prediction"
admin.site.site_title = "PA Labor Injury Prediction Admin Portal"
admin.site.index_title = "Welcome to PA Labor Injury Prediction Portal"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", PreprocessSiteView.as_view(), name="preprocess-site"),
    path("preprocess/", include("preprocess_module.urls")),
    path("prediction/", include("prediction_module.urls")),
    path("neural/", include("neural_module.urls")),
    path("api/", include(router.urls)),
]
