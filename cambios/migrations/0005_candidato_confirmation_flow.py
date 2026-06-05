# Generated manually 2026-06-02 — flujo de confirmacion del candidato.
#
# Refactor mayor del flujo de SolicitudCambio:
# - Agrega estado ESPERANDO_CANDIDATO entre CON_PROPUESTAS y APROBADA.
#   Cuando el solicitante elige una opcion, no se ejecuta el swap todavia;
#   el candidato propuesto debe confirmar/rechazar el intercambio.
# - Agrega campos a OpcionCambio:
#     * candidato: snapshot del monitor candidato al momento de proponer
#     * estado_candidato: pendiente | elegida | aceptada | rechazada | descartada
#     * fecha_decision_candidato

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def snapshot_candidatos(apps, schema_editor):
    """Llena el campo candidato en opciones existentes con el monitor actual de asignacion_swap."""
    OpcionCambio = apps.get_model("cambios", "OpcionCambio")
    for op in OpcionCambio.objects.select_related("asignacion_swap").all():
        if op.candidato_id is None and op.asignacion_swap_id is not None:
            op.candidato_id = op.asignacion_swap.monitor_id
            op.save(update_fields=["candidato"])


class Migration(migrations.Migration):

    dependencies = [
        ("cambios", "0004_opcion_cambio_y_estado_propuestas"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1) Agregar el nuevo estado a SolicitudCambio
        migrations.AlterField(
            model_name="solicitudcambio",
            name="estado",
            field=models.CharField(
                choices=[
                    ("pendiente", "Pendiente"),
                    ("con_propuestas", "Con propuestas"),
                    ("esperando_candidato", "Esperando confirmacion del candidato"),
                    ("aprobada", "Aprobada"),
                    ("rechazada", "Rechazada"),
                ],
                default="pendiente",
                max_length=24,
            ),
        ),
        # 2) Agregar campos nuevos a OpcionCambio
        migrations.AddField(
            model_name="opcioncambio",
            name="candidato",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="opciones_como_candidato",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="opcioncambio",
            name="estado_candidato",
            field=models.CharField(
                choices=[
                    ("pendiente", "Pendiente"),
                    ("elegida", "Elegida por solicitante"),
                    ("aceptada", "Aceptada por candidato"),
                    ("rechazada", "Rechazada por candidato"),
                    ("descartada", "Descartada"),
                ],
                default="pendiente",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="opcioncambio",
            name="fecha_decision_candidato",
            field=models.DateTimeField(blank=True, null=True),
        ),
        # 3) Snapshot del candidato para opciones existentes
        migrations.RunPython(snapshot_candidatos, migrations.RunPython.noop),
    ]
