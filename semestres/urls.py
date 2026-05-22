from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'semestres', views.SemestreViewSet, basename='semestre')

urlpatterns = router.urls
