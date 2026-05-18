from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from django.http import HttpResponseForbidden

from usuarios.models import Usuario

from .forms import ResponderSolicitudForm, SolicitudCambioForm
from .models import SolicitudCambio
from .services import aprobar_solicitud, crear_solicitud_cambio, rechazar_solicitud


def role_required(expected_role):
	"""Decorador para verificar el rol del usuario."""
	from functools import wraps

	def decorator(view_func):
		@wraps(view_func)
		@login_required
		def _wrapped(request, *args, **kwargs):
			if request.user.rol != expected_role:
				raise PermissionDenied
			return view_func(request, *args, **kwargs)
		return _wrapped
	return decorator


admin_required = role_required(Usuario.ADMIN)
monitor_required = role_required(Usuario.MONITOR)


# =========================
# VISTAS PARA MONITORES
# =========================

@monitor_required
@require_http_methods(["GET", "POST"])
def crear_solicitud_view(request):
	"""Vista para que un monitor cree una solicitud de cambio de turno."""
	if request.method == "POST":
		form = SolicitudCambioForm(request.POST, monitor=request.user)
		if form.is_valid():
			try:
				form.save()
				messages.success(request, "Solicitud de cambio creada exitosamente.")
				return redirect("mis_solicitudes")
			except ValidationError as exc:
				messages.error(request, str(exc))
	else:
		form = SolicitudCambioForm(monitor=request.user)

	return render(request, "cambios/crear_solicitud.html", {
		"form": form,
	})


@monitor_required
@require_http_methods(["GET"])
def mis_solicitudes_view(request):
	"""Vista para que un monitor vea sus solicitudes de cambio."""
	solicitudes = SolicitudCambio.objects.filter(
		solicitante=request.user
	).select_related(
		"asignacion__horario", "asignacion__semestre", "monitor_reemplazo"
	).order_by("-fecha_creacion")

	return render(request, "cambios/mis_solicitudes.html", {
		"solicitudes": solicitudes,
	})


@monitor_required
@require_http_methods(["GET"])
def mis_asignaciones_view(request):
	"""Vista para que un monitor vea sus asignaciones de turno."""
	asignaciones = request.user.asignaciones.select_related(
		"horario__sala", "semestre"
	).order_by("semestre__anio", "semestre__periodo", "horario__dia_semana", "horario__hora_inicio")

	return render(request, "cambios/mis_asignaciones.html", {
		"asignaciones": asignaciones,
	})


# =========================
# VISTAS PARA ADMINISTRADORES
# =========================

@admin_required
@require_http_methods(["GET"])
def lista_solicitudes_view(request):
	"""Vista para que el administrador vea todas las solicitudes."""
	solicitudes = SolicitudCambio.objects.select_related(
		"asignacion__horario", "asignacion__semestre",
		"solicitante", "monitor_reemplazo"
	).order_by("-fecha_creacion")

	return render(request, "cambios/lista_solicitudes.html", {
		"solicitudes": solicitudes,
	})


@admin_required
@require_http_methods(["GET", "POST"])
def responder_solicitud_view(request, id_cambio):
	"""Vista para que el administrador apruebe o rechace una solicitud."""
	solicitud = get_object_or_404(SolicitudCambio, pk=id_cambio)

	if solicitud.estado != SolicitudCambio.PENDIENTE:
		messages.warning(request, "Esta solicitud ya fue respondida.")
		return redirect("lista_solicitudes")

	if request.method == "POST":
		form = ResponderSolicitudForm(request.POST)
		if form.is_valid():
			estado = form.cleaned_data["estado"]
			respuesta = form.cleaned_data["respuesta"]
			try:
				if estado == SolicitudCambio.APROBADA:
					aprobar_solicitud(
						solicitud=solicitud,
						admin=request.user,
						respuesta=respuesta,
					)
					messages.success(request, "Solicitud aprobada exitosamente.")
				else:
					rechazar_solicitud(
						solicitud=solicitud,
						admin=request.user,
						respuesta=respuesta,
					)
					messages.success(request, "Solicitud rechazada exitosamente.")
				return redirect("lista_solicitudes")
			except ValidationError as exc:
				messages.error(request, str(exc))
	else:
		form = ResponderSolicitudForm()

	return render(request, "cambios/responder_solicitud.html", {
		"solicitud": solicitud,
		"form": form,
	})


@admin_required
@require_http_methods(["GET"])
def detalle_solicitud_view(request, id_cambio):
	"""Vista para que el administrador vea los detalles de una solicitud."""
	solicitud = get_object_or_404(SolicitudCambio, pk=id_cambio)
	return render(request, "cambios/detalle_solicitud.html", {
		"solicitud": solicitud,
	})
