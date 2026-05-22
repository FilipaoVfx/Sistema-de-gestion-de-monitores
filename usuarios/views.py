import logging
import secrets
import string

from django.conf import settings
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.db import transaction
from rest_framework import generics, permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from asgiref.sync import async_to_sync

from .models import Usuario
from .serializers import CrearMonitorSerializer, LoginSerializer, UsuarioSerializer


def _generate_temp_password(length: int = 10) -> str:
    """Genera una password temporal aleatoria (letras + dígitos)."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    """POST /api/auth/login/  →  { token, user }"""
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    email = serializer.validated_data['email']
    password = serializer.validated_data['password']

    user = authenticate(request, username=email, password=password)
    if user is None:
        return Response({'error': 'Credenciales inválidas.'}, status=status.HTTP_401_UNAUTHORIZED)

    token, _ = Token.objects.get_or_create(user=user)
    return Response({
        'token': token.key,
        'user': UsuarioSerializer(user).data,
    })


@api_view(['POST'])
def logout_view(request):
    """POST /api/auth/logout/  →  204"""
    try:
        request.user.auth_token.delete()
    except Exception:
        pass
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
def me_view(request):
    """GET /api/auth/me/  →  user info"""
    return Response(UsuarioSerializer(request.user).data)


@api_view(['POST'])
def debug_ping_view(request):
    """POST /api/auth/debug-ping/  →  sentinela para verificar que el deploy
    actual ejecuta codigo. Retorna info del request.user sin tocar la DB."""
    user = request.user
    return Response({
        'sentinel': '9f3466a-or-newer',
        'authenticated': bool(user and user.is_authenticated),
        'email': getattr(user, 'email', None),
        'rol': getattr(user, 'rol', None),
        'is_admin_check': getattr(user, 'rol', None) == Usuario.ADMIN,
        'usuario_admin_const': Usuario.ADMIN,
    })


# ---------------------------------------------------------------------------
# User management (admin only)
# ---------------------------------------------------------------------------

class UsuarioViewSet(viewsets.ReadOnlyModelViewSet):
    """
    list     GET /api/usuarios/        → todos los usuarios (admin) o solo yo (monitor)
    retrieve GET /api/usuarios/{id}/
    """
    serializer_class = UsuarioSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.rol == Usuario.ADMIN:
            return Usuario.objects.all().order_by('email')
        return Usuario.objects.filter(pk=user.pk)


class CrearMonitorView(generics.CreateAPIView):
    """POST /api/usuarios/monitores/

    Crea un monitor con una password temporal autogenerada y la retorna
    en la respuesta (campo `temporary_password`). El admin debe entregarla
    al monitor por un canal seguro (Slack/WhatsApp/etc); el monitor podra
    cambiarla luego desde su perfil.

    Adicionalmente intenta enviar un correo de bienvenida con la password
    temporal, pero el endpoint no falla si SMTP no esta configurado.
    """
    serializer_class = CrearMonitorSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        # Outer try/except como red de seguridad: cualquier excepcion no
        # capturada en otro lado se reporta aqui con tipo+msg+traceback corto.
        import traceback
        try:
            if request.user.rol != Usuario.ADMIN:
                return Response({'error': 'Solo administradores pueden crear monitores.'}, status=403)

            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data

            # Password: si admin la provee usa esa, sino genera una temporal
            temp_password = (request.data.get('password') or '').strip() or _generate_temp_password()

            # Usamos el patron de seed_demo: set_password despues de crear,
            # en una transaccion atomica para evitar usuarios huerfanos.
            with transaction.atomic():
                monitor = Usuario.objects.create_user(
                    username=data['email'],
                    email=data['email'],
                    password=None,
                    cedula=data['cedula'],
                    first_name=data.get('first_name', ''),
                    last_name=data.get('last_name', ''),
                    telefono=data.get('telefono', ''),
                    rol=Usuario.MONITOR,
                    is_active=True,
                )
                monitor.set_password(temp_password)
                monitor.save(update_fields=['password'])

            # Best-effort: intenta mandar correo. No bloquea la respuesta.
            try:
                site_url = getattr(settings, 'SITE_URL', '').rstrip('/')
                text_message = (
                    f"Hola {monitor.first_name},\n\n"
                    "Tu cuenta de monitor fue creada en SGMSC.\n"
                    f"Usuario: {monitor.email}\n"
                    f"Contrasena temporal: {temp_password}\n\n"
                    "Por seguridad, cambia tu contrasena al iniciar sesion."
                    + (f"\nLogin: {site_url}/usuarios/login/" if site_url else "")
                )
                send_mail(
                    "Bienvenido al SGMSC - Tu contrasena temporal",
                    text_message,
                    getattr(settings, 'EMAIL_HOST_USER', None) or 'no-reply@sgmsc.local',
                    [monitor.email],
                    fail_silently=True,
                )
            except Exception:
                logger.exception("Error enviando correo de bienvenida para %s", monitor.email)

            payload = UsuarioSerializer(monitor).data
            payload['temporary_password'] = temp_password
            return Response(payload, status=status.HTTP_201_CREATED)

        except Exception as exc:
            logger.exception("Error inesperado creando monitor")
            return Response(
                {
                    'error': 'Error inesperado al crear monitor',
                    'type': type(exc).__name__,
                    'detail': str(exc),
                    'traceback': traceback.format_exc()[-1500:],
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ---------------------------------------------------------------------------
# AI chat (admin only)
# ---------------------------------------------------------------------------

@api_view(['POST'])
def ai_chat_view(request):
    """POST /api/ai/chat/  →  { response }"""
    if request.user.rol != Usuario.ADMIN:
        return Response({'error': 'No tienes permisos.'}, status=403)

    user_message = request.data.get('message', '').strip()
    if not user_message:
        return Response({'error': 'Mensaje vacío.'}, status=400)

    try:
        from AI_implementation.ai_orchestrator import get_ai_response
        ai_response = async_to_sync(get_ai_response)(
            user_message=user_message,
            session_id=request.user.username,
        )
        return Response({'success': True, 'response': ai_response})
    except Exception as exc:
        logger.exception("Error en ai_chat_view: %s", exc)
        return Response({'error': 'Error interno del servidor.'}, status=500)
