"""
URL configuration for TiffinTrail project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('chef/', include('chef.urls', namespace='chef')),
    path('adminpanel/', include('adminpanel.urls', namespace='adminpanel')),
    path('', include('customer.urls', namespace='customer')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
