from rest_framework import viewsets, permissions
from .models import Semestre
from .serializers import SemestreSerializer


class SemestreViewSet(viewsets.ModelViewSet):
    queryset = Semestre.objects.all().order_by('-anio', '-periodo')
    serializer_class = SemestreSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id_semestre'
