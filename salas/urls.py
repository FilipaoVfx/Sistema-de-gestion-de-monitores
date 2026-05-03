from django.urls import path
from . import views

urlpatterns = [
    path("",               views.salas,        name="salas"),
    path("<int:id_sala>/", views.sala_detalle,  name="sala-detalle"),
]