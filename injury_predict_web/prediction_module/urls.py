from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from prediction_module import views
from prediction_module.views import PredictionSiteView, ReportView, StatsView

urlpatterns = [
    path("", PredictionSiteView.as_view(), name="prediction-site"),
    path("stats/", StatsView.as_view(), name="stats-site"),
    path("report/", ReportView.as_view(), name="report-site"),
    path("evaluation/<int:id>", views.get_evaluation_file, name="evaluation"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
