from django.db import models

# Create your models here.
class Sala(models.Model):
    id_sala = models.AutoField(primary_key=True)
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    capacidad = models.PositiveIntegerField()

    class Meta:
        db_table = "sala"
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} — {self.nombre} ({self.capacidad} puestos)"