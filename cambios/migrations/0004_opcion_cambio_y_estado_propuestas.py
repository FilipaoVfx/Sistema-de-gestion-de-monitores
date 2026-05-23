# Generated manually 2026-05-22 — modelo OpcionCambio + estado con_propuestas.
#
# Cambio de modelo: en vez de elegir UN reemplazo al aprobar, el admin propone
# 2+ opciones de swap (cada una con OTRA asignacion existente). El monitor
# solicitante elige cual swap acepta. Al elegir se ejecuta el swap atomico
# y la solicitud queda APROBADA.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("asignaciones", "0002_alter_asignacion_semestre_delete_semestre"),
        ("cambios", "0003_alter_solicitudcambio_monitor_reemplazo"),
    ]

    operations = [
        # 1) Agregar estado con_propuestas a SolicitudCambio
        migrations.AlterField(
            model_name="solicitudcambio",
            name="estado",
            field=models.CharField(
                choices=[
                    ("pendiente", "Pendiente"),
                    ("con_propuestas", "Con propuestas"),
                    ("aprobada", "Aprobada"),
                    ("rechazada", "Rechazada"),
                ],
                default="pendiente",
                max_length=16,
            ),
        ),
        # 2) Crear tabla OpcionCambio
        migrations.CreateModel(
            name="OpcionCambio",
            fields=[
                ("id_opcion", models.AutoField(primary_key=True, serialize=False)),
                ("orden", models.PositiveSmallIntegerField(default=1)),
                ("seleccionada", models.BooleanField(default=False)),
                ("fecha_creacion", models.DateTimeField(auto_now_add=True)),
                (
                    "asignacion_swap",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="opciones_swap",
                        to="asignaciones.asignacion",
                    ),
                ),
                (
                    "solicitud",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="opciones",
                        to="cambios.solicitudcambio",
                    ),
                ),
            ],
            options={
                "ordering": ["solicitud", "orden"],
            },
        ),
        migrations.AddConstraint(
            model_name="opcioncambio",
            constraint=models.UniqueConstraint(
                fields=("solicitud", "asignacion_swap"),
                name="unique_asignacion_swap_per_solicitud",
            ),
        ),
        migrations.AddConstraint(
            model_name="opcioncambio",
            constraint=models.UniqueConstraint(
                condition=models.Q(("seleccionada", True)),
                fields=("solicitud",),
                name="unique_selected_opcion_per_solicitud",
            ),
        ),
    ]
