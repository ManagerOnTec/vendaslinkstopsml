from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.urls import re_path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('produtos.urls')),
    # Servir favicon em ambos os ambientes (dev e prod)
    re_path(r'^favicon\.ico$', serve, {'document_root': settings.STATIC_ROOT, 'path': 'favicon.ico'}),
    re_path(r'^favicon\.png$', serve, {'document_root': settings.STATIC_ROOT, 'path': 'favicon.png'}),
]

# Servir media files em desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
