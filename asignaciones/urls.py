from django.urls import path

from . import views

urlpatterns = [
	path("crear/", views.crear_asignacion_view, name="crear_asignacion"),
]
