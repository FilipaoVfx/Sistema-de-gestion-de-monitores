from functools import wraps

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.mail import send_mail
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.crypto import get_random_string
from django.views.decorators.http import require_http_methods

from .forms import MonitorCreationForm
from .models import Usuario


def role_required(expected_role):
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


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            return redirect('post_login_router')
        return render(request, 'usuarios/login.html', {'error': 'Credenciales invalidas.'})

    return render(request, 'usuarios/login.html')


@login_required
def post_login_router(request):
    if request.user.rol == Usuario.ADMIN:
        return redirect('admin_dashboard')
    if request.user.rol == Usuario.MONITOR:
        return redirect('monitor_dashboard')
    raise PermissionDenied


@admin_required
@require_http_methods(["GET", "POST"])
def crear_monitor_view(request):
    if request.method == 'POST':
        form = MonitorCreationForm(request.POST)
        if form.is_valid():
            # Generate a temporary password for first access.
            temp_password = get_random_string(10)

            # Create the monitor with the temporary password and enforced role.
            monitor = Usuario.objects.create_user(
                username=form.cleaned_data['email'],
                email=form.cleaned_data['email'],
                cedula=form.cleaned_data['cedula'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                telefono=form.cleaned_data['telefono'],
                rol=Usuario.MONITOR,
                password=temp_password,
            )

            # Send credentials directly via SMTP.
            subject = 'Bienvenido al SGM SC - Tus credenciales de acceso'
            message = (
                f"Hola {monitor.first_name},\n\n"
                "Tu cuenta de monitor fue creada.\n"
                f"Usuario: {monitor.email}\n"
                f"Contrasena temporal: {temp_password}\n\n"
                "Por favor inicia sesion y cambia tu contrasena lo antes posible."
            )
            send_mail(
                'Bienvenido al SGM SC - Tus credenciales de acceso', # Asunto
                f'Hola {monitor.first_name}, tu clave es: {temp_password}', # Mensaje
                settings.EMAIL_HOST_USER,  # <-- ¡ESTE ES EL REMITENTE! Vital que esté aquí
                [monitor.email],           # Destinatario
                fail_silently=False,
)

            messages.success(request, 'Monitor creado. Se envio el correo con credenciales.')
            return redirect('admin_dashboard')
    else:
        form = MonitorCreationForm()

    return render(request, 'usuarios/crear_monitor.html', {'form': form})


@admin_required
def admin_dashboard(request):
    return render(request, 'usuarios/admin_dashboard.html')


@monitor_required
def monitor_dashboard(request):
    return HttpResponse("Monitor dashboard")