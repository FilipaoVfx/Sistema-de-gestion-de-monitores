from datetime import datetime, time

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from horarios.models import Horario
from salas.models import Sala
from semestres.models import Semestre
from usuarios.models import Usuario
from usuarios.views import admin_required

from .forms import CrearAsignacionesForm
from .models import Asignacion


def _fmt_hora(hora) -> str:
	return hora.strftime("%H:%M")


def _parse_hora_str(value: str) -> time:
	return datetime.strptime(value, "%H:%M").time()


@admin_required
@require_http_methods(["GET", "POST"])
def crear_asignacion_view(request):
	salas = list(Sala.objects.all().order_by("codigo"))
	monitores = list(Usuario.objects.filter(rol=Usuario.MONITOR).order_by("email"))
	semestres_qs = Semestre.objects.order_by("-anio", "-periodo")

	semestre_activo = semestres_qs.filter(activo=True).first()
	semestre_default = semestre_activo or semestres_qs.first()

	selected_sala_id = request.GET.get("sala_id") or request.POST.get("sala_id")
	selected_semestre_id = request.GET.get("semestre") or request.POST.get("semestre")
	selected_monitor_email = request.GET.get("monitor")

	if not selected_semestre_id and semestre_default is not None:
		selected_semestre_id = str(semestre_default.pk)

	selected_sala = None
	sala_display = ""
	if selected_sala_id:
		selected_sala = Sala.objects.filter(id_sala=selected_sala_id).first()
		if selected_sala is not None:
			sala_display = f"{selected_sala.codigo} - {selected_sala.nombre}"

	selected_semestre = None
	if selected_semestre_id:
		selected_semestre = Semestre.objects.filter(pk=selected_semestre_id).first()

	if request.method == "POST":
		form = CrearAsignacionesForm(
			request.POST,
			monitor_queryset=Usuario.objects.filter(rol=Usuario.MONITOR).order_by("email"),
			semestre_queryset=semestres_qs,
		)

		if form.is_valid():
			monitor = form.cleaned_data["monitor"]
			semestre = form.cleaned_data["semestre"]
			sala_id = form.cleaned_data["sala_id"]
			selecciones = form.cleaned_data["horarios"]

			existing_ids: list[int] = []
			nuevos: list[tuple[int, time, time]] = []
			for token in selecciones:
				if token.startswith("h:"):
					existing_ids.append(int(token[2:]))
					continue
				# n:<dia>|<HH:MM>|<HH:MM>
				rest = token[2:]
				dia_str, inicio_str, fin_str = rest.split("|")
				nuevos.append(
					(int(dia_str), _parse_hora_str(inicio_str), _parse_hora_str(fin_str))
				)

			horarios_existentes = list(
				Horario.objects.filter(
					id_horario__in=existing_ids,
					sala_id=sala_id,
				)
			)
			if len(horarios_existentes) != len(set(existing_ids)):
				form.add_error(None, "Hay bloques seleccionados que no pertenecen a la sala escogida.")
			else:
				horarios_creados: list[Horario] = []
				for dia_semana, hora_inicio, hora_fin in nuevos:
					existing = Horario.objects.filter(
						sala_id=sala_id,
						dia_semana=dia_semana,
						hora_inicio=hora_inicio,
						hora_fin=hora_fin,
					).first()
					if existing is not None:
						horarios_creados.append(existing)
						continue

					overlap = Horario.objects.filter(
						sala_id=sala_id,
						dia_semana=dia_semana,
						hora_inicio__lt=hora_fin,
						hora_fin__gt=hora_inicio,
					).exists()
					if overlap:
						form.add_error(
							None,
							"Hay un bloque seleccionado que se cruza con un horario ya existente en la sala.",
						)
						break

					try:
						horarios_creados.append(
							Horario.objects.create(
								sala_id=sala_id,
								dia_semana=dia_semana,
								hora_inicio=hora_inicio,
								hora_fin=hora_fin,
							)
						)
					except IntegrityError:
						form.add_error(
							None,
							"No se pudieron crear algunos horarios por conflicto. Recarga la grilla y reintenta.",
						)
						break
					except ValidationError as exc:
						form.add_error(None, "; ".join(exc.messages) if exc.messages else str(exc))
						break

				if not form.errors:
					horarios_final = {h.id_horario: h for h in (horarios_existentes + horarios_creados)}
					horario_ids = list(horarios_final.keys())

					ocupados = set(
						Asignacion.objects.filter(
							horario_id__in=horario_ids,
							semestre=semestre,
						).values_list("horario_id", flat=True)
					)
					if ocupados:
						form.add_error(
							None,
							"Algunos bloques ya están ocupados para ese periodo. Recarga la grilla y vuelve a intentar.",
						)
					else:
						nuevas = [
							Asignacion(monitor=monitor, horario=horarios_final[hid], semestre=semestre)
							for hid in horario_ids
						]

						errores = []
						for asignacion in nuevas:
							try:
								asignacion.full_clean()
							except ValidationError as exc:
								errores.append("; ".join(exc.messages) if exc.messages else str(exc))

						if errores:
							form.add_error(None, " ".join(errores))
						else:
							try:
								with transaction.atomic():
									for asignacion in nuevas:
										asignacion.save(validate=False)
							except IntegrityError:
								form.add_error(
									None,
									"No se pudieron guardar las asignaciones (posible conflicto). Recarga la grilla y reintenta.",
								)
							else:
								messages.success(
									request,
									f"Asignaciones creadas correctamente: {len(nuevas)}.",
								)
								return redirect("admin_dashboard")
	else:
		initial = {}
		if selected_monitor_email:
			initial["monitor"] = selected_monitor_email
		if selected_semestre_id:
			initial["semestre"] = selected_semestre_id
		if selected_sala is not None:
			initial["sala"] = sala_display
			initial["sala_id"] = selected_sala.id_sala

		form = CrearAsignacionesForm(
			initial=initial,
			monitor_queryset=Usuario.objects.filter(rol=Usuario.MONITOR).order_by("email"),
			semestre_queryset=semestres_qs,
		)

	# Construcción de grilla para la sala/semestre seleccionados
	dias = list(getattr(Horario, "DIAS", []))
	grid_rows = []
	asignaciones_por_horario = {}
	selected_keys_set: set[str] = set()

	# Mantener selección en caso de POST inválido
	if request.method == "POST":
		raw_selected = request.POST.get("horarios") or ""
		selected_keys_set = {x.strip() for x in raw_selected.split(",") if x.strip()}

	if selected_sala is not None and selected_semestre is not None:
		horarios_sala = list(
			Horario.objects.filter(sala=selected_sala)
			.order_by("hora_inicio", "hora_fin", "dia_semana")
		)

		asignaciones = list(
			Asignacion.objects.filter(
				semestre=selected_semestre,
				horario__sala=selected_sala,
			).select_related("monitor", "horario")
		)
		asignaciones_por_horario = {a.horario_id: a for a in asignaciones}

		# Franjas (hora_inicio, hora_fin): si la sala no tiene, usar global; si no hay global, usar defaults.
		default_franjas = {
			(time(8, 0), time(10, 0)),
			(time(10, 0), time(12, 0)),
			(time(12, 0), time(14, 0)),
			(time(14, 0), time(16, 0)),
			(time(16, 0), time(18, 0)),
			(time(20, 0), time(22, 0)),
		}
		sala_franjas = {(h.hora_inicio, h.hora_fin) for h in horarios_sala}
		global_franjas = set(
			Horario.objects.values_list("hora_inicio", "hora_fin").distinct()
		)
		franjas = sorted(default_franjas | global_franjas | sala_franjas, key=lambda x: (x[0], x[1]))

		# Mapa (dia, inicio, fin) -> Horario
		horario_map = {
			(h.dia_semana, h.hora_inicio, h.hora_fin): h
			for h in horarios_sala
		}

		# Para bloquear creación de franjas que se cruzan con un horario ya existente.
		horarios_por_dia: dict[int, list[Horario]] = {}
		for h in horarios_sala:
			horarios_por_dia.setdefault(h.dia_semana, []).append(h)

		for inicio, fin in franjas:
			row = {
				"label": f"{_fmt_hora(inicio)} - {_fmt_hora(fin)}",
				"inicio": inicio,
				"fin": fin,
				"cells": [],
			}
			for dia_value, _dia_label in dias:
				horario = horario_map.get((dia_value, inicio, fin))
				if horario is not None:
					asignacion = asignaciones_por_horario.get(horario.id_horario)
					if asignacion is not None:
						monitor_name = asignacion.monitor.get_full_name() or asignacion.monitor.email
						row["cells"].append(
							{
								"status": "occupied",
								"horario_id": horario.id_horario,
								"monitor": monitor_name,
								"monitor_email": asignacion.monitor.email,
							}
						)
					else:
						row["cells"].append(
							{
								"status": "available",
								"key": f"h:{horario.id_horario}",
								"horario_id": horario.id_horario,
							}
						)
					continue

				# No existe horario exacto: permitir crear si no se cruza con uno existente.
				overlap = any(
					h.hora_inicio < fin and h.hora_fin > inicio
					for h in horarios_por_dia.get(dia_value, [])
				)
				if overlap:
					row["cells"].append({"status": "none"})
				else:
					row["cells"].append(
						{
							"status": "available",
							"key": f"n:{dia_value}|{_fmt_hora(inicio)}|{_fmt_hora(fin)}",
						}
					)

			grid_rows.append(row)

	context = {
		"form": form,
		"salas": salas,
		"monitores": monitores,
		"selected_sala": selected_sala,
		"selected_semestre": selected_semestre,
		"dias": dias,
		"grid_rows": grid_rows,
		"selected_keys": selected_keys_set,
		"sala_display": sala_display,
	}
	return render(request, "asignaciones/crear_asignacion.html", context)
