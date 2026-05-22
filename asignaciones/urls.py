from rest_framework.routers import SimpleRouter
from . import views

router = SimpleRouter()
router.register(r'asignaciones', views.AsignacionViewSet, basename='asignacion')

urlpatterns = router.urls
