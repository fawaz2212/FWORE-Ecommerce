"""
URL configuration for ecommerce project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
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
from django.urls import path, include, re_path
from django.conf import settings
from django.http import FileResponse, Http404
from django.utils._os import safe_join
from pathlib import Path


def product_media(request, path):
    try:
        file_path = Path(safe_join(str(settings.MEDIA_ROOT), path))

        if not file_path.is_file():
            raise Http404("Image not found")

        return FileResponse(open(file_path, "rb"))
    except (ValueError, OSError):
        raise Http404("Image not found")


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('store.urls')),
    re_path(r'^media/(?P<path>.*)$', product_media),
    path('api/', include('api.urls')),
]

