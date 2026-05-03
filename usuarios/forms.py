from django import forms

from .models import Usuario


class MonitorCreationForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['first_name', 'last_name', 'cedula', 'email', 'telefono']
        labels = {
            'first_name': 'Nombre',
            'last_name': 'Apellido',
            'cedula': 'Cedula',
            'email': 'Email',
            'telefono': 'Telefono',
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'cedula': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
        }
