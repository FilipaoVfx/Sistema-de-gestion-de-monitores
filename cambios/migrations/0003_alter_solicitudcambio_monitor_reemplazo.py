# Generated manually 2026-05-22 — hace monitor_reemplazo nullable.
#
# Antes el monitor debia elegir el reemplazo al crear la solicitud, pero
# los monitores no tienen acceso a la lista de otros usuarios. Ahora el
# monitor solo solicita el cambio (asignacion + motivo) y el admin asigna
# el reemplazo al aprobar.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cambios", "0002_solicitudcambio_unique_pending_solicitud_per_asignacion"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="solicitudcambio",
            name="monitor_reemplazo",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="solicitudes_reemplazo",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
