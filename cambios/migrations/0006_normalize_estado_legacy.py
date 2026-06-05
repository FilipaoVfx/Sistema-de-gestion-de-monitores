# Generated manually 2026-06-05 — normaliza solicitudes legacy en ESPERANDO_CANDIDATO.
#
# El flujo del 2026-06-02 introdujo el estado ESPERANDO_CANDIDATO para esperar
# que el monitor candidato confirmara el swap. Ese flujo se simplifico el
# 2026-06-05 (commit 30a4cdf): el swap ahora se ejecuta directamente cuando
# el solicitante elige. Para que las solicitudes que quedaron a medio camino
# puedan resolverse con el flujo nuevo, las regresamos a CON_PROPUESTAS y
# marcamos sus opciones ELEGIDA como PENDIENTE (para que el solicitante
# pueda elegir de nuevo y el swap se ejecute).

from django.db import migrations


def normalize_legacy(apps, schema_editor):
    SolicitudCambio = apps.get_model("cambios", "SolicitudCambio")
    OpcionCambio   = apps.get_model("cambios", "OpcionCambio")

    # 1) Solicitudes en ESPERANDO_CANDIDATO -> CON_PROPUESTAS
    legacy_solicitudes = SolicitudCambio.objects.filter(estado="esperando_candidato")
    count_sol = legacy_solicitudes.update(estado="con_propuestas")

    # 2) Opciones que quedaron en ELEGIDA -> PENDIENTE (para que sean elegibles)
    count_op = OpcionCambio.objects.filter(estado_candidato="elegida").update(
        estado_candidato="pendiente",
    )

    print(f"   normalize_legacy: {count_sol} solicitudes y {count_op} opciones revertidas")


def reverse_noop(apps, schema_editor):
    """No hay reverso util: la informacion de quien estaba en que estado se
    pierde al fundir ESPERANDO_CANDIDATO en CON_PROPUESTAS."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("cambios", "0005_candidato_confirmation_flow"),
    ]

    operations = [
        migrations.RunPython(normalize_legacy, reverse_noop),
    ]
