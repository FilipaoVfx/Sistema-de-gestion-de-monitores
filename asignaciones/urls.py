from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'asignaciones', views.AsignacionViewSet, basename='asignacion')

urlpatterns = router.urls
