import logging

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import generics, permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from asgiref.sync import async_to_sync

from .models import Usuario
from .serializers import CrearMonitorSerializer, LoginSerializer, UsuarioSerializer

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
    """POST /api/usuarios/monitores/  →  crea monitor y envía correo de activación"""
    serializer_class = CrearMonitorSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        if request.user.rol != Usuario.ADMIN:
            return Response({'error': 'Solo administradores pueden crear monitores.'}, status=403)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        monitor = Usuario.objects.create_user(
            username=data['email'],
            email=data['email'],
            cedula=data['cedula'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            telefono=data.get('telefono', ''),
            rol=Usuario.MONITOR,
            password=None,
        )

        # Generate password reset link for first-time activation
        token_generator = PasswordResetTokenGenerator()
        uid = urlsafe_base64_encode(force_bytes(monitor.pk))
        token = token_generator.make_token(monitor)
        reset_path = reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
        site_url = settings.SITE_URL.rstrip('/')
        reset_url = f"{site_url}{reset_path}"

        html_message = render_to_string(
            'emails/bienvenida_monitor.html',
            {'first_name': monitor.first_name, 'email': monitor.email, 'reset_url': reset_url},
        )
        text_message = (
            f"Hola {monitor.first_name},\n\n"
            "Tu cuenta de monitor fue creada.\n"
            f"Usuario: {monitor.email}\n\n"
            "Para establecer tu contraseña, visita el siguiente enlace:\n"
            f"{reset_url}\n\n"
            "El enlace expirará en 1 hora."
        )

        try:
            send_mail(
                "Bienvenido al SGM SC - Establece tu contraseña",
                text_message,
                settings.EMAIL_HOST_USER,
                [monitor.email],
                html_message=html_message,
                fail_silently=False,
            )
        except Exception:
            logger.exception("Error enviando correo de activación para %s", monitor.email)
            monitor.delete()
            return Response(
                {'error': 'No se pudo enviar el correo de activación. El monitor no fue creado.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(UsuarioSerializer(monitor).data, status=status.HTTP_201_CREATED)


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
