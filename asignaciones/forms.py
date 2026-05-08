from datetime import datetime

from django import forms

from salas.models import Sala
from semestres.models import Semestre
from usuarios.models import Usuario


MONITOR_DATALIST_ID = "monitorEmails"
SALA_DATALIST_ID = "salaComputoList"


class CrearAsignacionesForm(forms.Form):
    monitor = forms.ModelChoiceField(
        queryset=Usuario.objects.none(),
        to_field_name="email",
        label="Correo del monitor",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "list": MONITOR_DATALIST_ID,
                "placeholder": "Escribe y selecciona el correo del monitor",
                "autocomplete": "off",
            }
        ),
    )

    sala = forms.CharField(
        label="Sala de cómputo",
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "list": SALA_DATALIST_ID,
                "placeholder": "Busca por código o nombre (ej: SALA-101 o Laboratorio)",
                "autocomplete": "off",
            }
        ),
    )
    sala_id = forms.IntegerField(required=False, widget=forms.HiddenInput())

    semestre = forms.ModelChoiceField(
        queryset=Semestre.objects.none(),
        label="Periodo académico",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    horarios = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={"id": "selectedHorarios"}),
    )

    def __init__(self, *args, monitor_queryset=None, semestre_queryset=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["monitor"].queryset = (
            monitor_queryset
            if monitor_queryset is not None
            else Usuario.objects.filter(rol=Usuario.MONITOR).order_by("email")
        )
        self.fields["monitor"].error_messages["invalid_choice"] = (
            "Selecciona un correo válido de la lista."
        )

        self.fields["semestre"].queryset = (
            semestre_queryset
            if semestre_queryset is not None
            else Semestre.objects.order_by("-anio", "-periodo")
        )

    def clean_horarios(self):
        raw = (self.cleaned_data.get("horarios") or "").strip()
        if not raw:
            return []

        tokens = [t.strip() for t in raw.split(",") if t.strip()]

        # Unificar y mantener orden
        seen = set()
        unique_tokens = []
        for token in tokens:
            if token in seen:
                continue
            seen.add(token)
            unique_tokens.append(token)

        for token in unique_tokens:
            if token.startswith("h:"):
                if not token[2:].isdigit():
                    raise forms.ValidationError("Selección de horarios inválida.")
                continue

            if token.startswith("n:"):
                parts = token[2:].split("|")
                if len(parts) != 3:
                    raise forms.ValidationError("Selección de horarios inválida.")
                dia_str, inicio_str, fin_str = parts
                if not dia_str.isdigit():
                    raise forms.ValidationError("Selección de horarios inválida.")
                try:
                    inicio = datetime.strptime(inicio_str, "%H:%M").time()
                    fin = datetime.strptime(fin_str, "%H:%M").time()
                except ValueError as exc:
                    raise forms.ValidationError("Selección de horarios inválida.") from exc
                if fin <= inicio:
                    raise forms.ValidationError("Selección de horarios inválida.")
                continue

            raise forms.ValidationError("Selección de horarios inválida.")

        return unique_tokens

    def clean(self):
        cleaned = super().clean()

        sala_id = cleaned.get("sala_id")
        if not sala_id or not Sala.objects.filter(id_sala=sala_id).exists():
            self.add_error("sala", "Selecciona una sala válida de la lista.")

        horarios = cleaned.get("horarios") or []
        if not horarios:
            raise forms.ValidationError("Selecciona al menos un bloque horario en la grilla.")

        return cleaned
