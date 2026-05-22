from django.contrib.auth import views as auth_views
from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'usuarios', views.UsuarioViewSet, basename='usuario')

urlpatterns = [
    # Auth
    path('auth/login/', views.login_view, name='login'),
    path('auth/logout/', views.logout_view, name='logout'),
    path('auth/me/', views.me_view, name='me'),
    path('auth/debug-ping/', views.debug_ping_view, name='debug_ping'),

    # User management
    path('usuarios/monitores/', views.CrearMonitorView.as_view(), name='crear_monitor'),

    # AI chat
    path('ai/chat/', views.ai_chat_view, name='ai_chat'),

    # Password reset (keeps Django built-in HTML views for email links to work)
    path(
        'auth/set-password/',
        auth_views.PasswordResetView.as_view(
            template_name='usuarios/password_reset_form.html',
            email_template_name='registration/password_reset_email.txt',
            html_email_template_name='registration/password_reset_email.html',
            subject_template_name='registration/password_reset_subject.txt',
        ),
        name='password_reset',
    ),
    path(
        'auth/set-password/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='usuarios/password_reset_done.html',
        ),
        name='password_reset_done',
    ),
    path(
        'auth/set-password/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='usuarios/set_password.html',
        ),
        name='password_reset_confirm',
    ),
    path(
        'auth/set-password/complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='usuarios/password_reset_complete.html',
        ),
        name='password_reset_complete',
    ),
] + router.urls
