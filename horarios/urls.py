from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'horarios', views.HorarioViewSet, basename='horario')

urlpatterns = router.urls
