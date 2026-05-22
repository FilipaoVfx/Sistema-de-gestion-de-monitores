from rest_framework import viewsets, permissions
from .models import Sala
from .serializers import SalaSerializer


class SalaViewSet(viewsets.ModelViewSet):
    queryset = Sala.objects.all().order_by('codigo')
    serializer_class = SalaSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id_sala'
