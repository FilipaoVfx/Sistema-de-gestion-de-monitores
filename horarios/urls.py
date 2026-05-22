from rest_framework.routers import SimpleRouter
from . import views

router = SimpleRouter()
router.register(r'horarios', views.HorarioViewSet, basename='horario')

urlpatterns = router.urls
