from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'cambios', views.SolicitudCambioViewSet, basename='cambio')

urlpatterns = router.urls
