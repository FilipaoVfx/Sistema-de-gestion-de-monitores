from rest_framework.routers import SimpleRouter
from . import views

router = SimpleRouter()
router.register(r'cambios', views.SolicitudCambioViewSet, basename='cambio')

urlpatterns = router.urls
