from django.contrib import admin

from .models import SolicitudCambio


@admin.register(SolicitudCambio)
class SolicitudCambioAdmin(admin.ModelAdmin):
	"""Panel de administración para SolicitudCambio."""

	list_display = (
		"id_cambio",
		"asignacion",
		"solicitante",
		"monitor_reemplazo",
		"estado",
		"fecha_creacion",
	)
	list_filter = (
		"estado",
		"tipo",
		"asignacion__semestre",
	)
	search_fields = (
		"solicitante__email",
		"monitor_reemplazo__email",
		"asignacion__horario__sala__codigo",
	)
	date_hierarchy = "fecha_creacion"
	readonly_fields = (
		"id_cambio",
		"fecha_creacion",
		"fecha_respuesta",
	)
	fieldsets = (
		("Información de la Solicitud", {
			"fields": (
				"id_cambio",
				"tipo",
				"asignacion",
				"motivo",
			),
		}),
		("Monitores", {
			"fields": (
				"solicitante",
				"monitor_reemplazo",
			),
		}),
		("Estado y Respuesta", {
			"fields": (
				"estado",
				"respuesta",
				"respondido_por",
				"fecha_respuesta",
			),
		}),
	)
