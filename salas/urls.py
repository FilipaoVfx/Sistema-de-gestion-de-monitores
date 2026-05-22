from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'salas', views.SalaViewSet, basename='sala')

urlpatterns = router.urls
