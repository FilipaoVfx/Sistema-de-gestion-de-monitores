from django import forms

from asignaciones.models import Asignacion
from usuarios.models import Usuario

from .models import SolicitudCambio


class SolicitudCambioForm(forms.ModelForm):
	"""Formulario para que un monitor cree una solicitud de cambio de turno."""

	monitor_reemplazo = forms.ModelChoiceField(
		queryset=Usuario.objects.filter(rol=Usuario.MONITOR),
		label="Monitor de Reemplazo",
		widget=forms.Select(attrs={"class": "form-select"}),
	)

	class Meta:
		model = SolicitudCambio
		fields = ["asignacion", "monitor_reemplazo", "motivo"]
		widgets = {
			"asignacion": forms.Select(attrs={"class": "form-select"}),
			"motivo": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
		}

	def __init__(self, *args, monitor=None, **kwargs):
		"""Inicializa el formulario con el monitor solicitante.

		Args:
			monitor: Usuario monitor que crea la solicitud.
		"""
		super().__init__(*args, **kwargs)
		self.monitor = monitor
		if monitor:
			self.fields["asignacion"].queryset = Asignacion.objects.filter(
				monitor=monitor
			).select_related("horario", "semestre")
			self.fields["monitor_reemplazo"].queryset = Usuario.objects.filter(
				rol=Usuario.MONITOR
			).exclude(pk=monitor.pk).order_by("first_name", "last_name", "email")
		else:
			self.fields["asignacion"].queryset = Asignacion.objects.none()

	def clean_asignacion(self):
		asignacion = self.cleaned_data.get("asignacion")
		if asignacion and self.monitor and asignacion.monitor_id != self.monitor.pk:
			raise forms.ValidationError("Solo puedes solicitar cambios de tus propias asignaciones.")
		return asignacion

	def save(self, commit=True):
		instancia = super().save(commit=False)
		instancia.solicitante = self.monitor
		instancia.tipo = SolicitudCambio.TIPO_CAMBIO_TURNO
		if commit:
			instancia.save()
		return instancia


class ResponderSolicitudForm(forms.Form):
	"""Formulario para que un administrador apruebe o rechace una solicitud."""

	ESTADOS_ADMIN = [
		(SolicitudCambio.APROBADA, "Aprobar"),
		(SolicitudCambio.RECHAZADA, "Rechazar"),
	]

	estado = forms.ChoiceField(
		label="Acción",
		choices=ESTADOS_ADMIN,
		widget=forms.Select(attrs={"class": "form-select"}),
	)
	respuesta = forms.CharField(
		label="Respuesta / Comentarios",
		widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
		required=False,
	)
