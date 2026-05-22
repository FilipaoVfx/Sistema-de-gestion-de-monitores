"""
URL configuration for sgmsc project — pure DRF JSON API.

All routes live under /api/.
Only the Django admin panel keeps its default path.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Django vanilla admin panel (kept as requested)
    path('admin/', admin.site.urls),

    # REST API
    path('api/', include('usuarios.urls')),
    path('api/', include('salas.urls')),
    path('api/', include('horarios.urls')),
    path('api/', include('semestres.urls')),
    path('api/', include('asignaciones.urls')),
    path('api/', include('cambios.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
