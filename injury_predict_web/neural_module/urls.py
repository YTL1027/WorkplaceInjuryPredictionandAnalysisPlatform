from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from neural_module.views import NeuralSiteView

urlpatterns = [
    path("neural/", NeuralSiteView.as_view(), name="neural-site"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
