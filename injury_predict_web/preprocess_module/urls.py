"""face_reco_site URL Configuration

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

from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from preprocess_module.views import PreprocessSiteView, HelpView

urlpatterns = [
    # path('', HomeView.as_view(), name='home'),
    # path('task', PreprocessView.as_view({'get': 'list', 'post': 'create','delete':'destroy'}),
    #      name='preprocess-task'),
    # path('task/delete/<int:id>', views.delete_item, name='delete'),
    # path('task/<string:name>', PreprocessSiteView.as_view(),
    #      name='preprocess-task-detail'),
    path("", PreprocessSiteView.as_view(), name="preprocess-site"),
    path("help/", HelpView.as_view(), name="help-site"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
