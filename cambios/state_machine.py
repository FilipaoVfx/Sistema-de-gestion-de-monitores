"""Maquina de estados para SolicitudCambio.

Define las transiciones permitidas, quien puede dispararlas y los invariantes
del estado de la solicitud. Aisla esa logica del servicio para que sea facil
auditar y testear.

Estados:
    PENDIENTE              - recien creada por el monitor solicitante
    CON_PROPUESTAS         - el admin propuso >=2 opciones de swap
    ESPERANDO_CANDIDATO    - solicitante eligio opcion X, candidato debe confirmar
    APROBADA               - candidato acepto y el swap se ejecuto (terminal)
    RECHAZADA              - admin rechazo en cualquier punto (terminal)

Transiciones permitidas:

      [solicitante crea]              [admin rechaza]
            |                                |
            v                                v
        PENDIENTE  --propose(admin)-->  CON_PROPUESTAS  -->  RECHAZADA
                                          |     ^
                                          |     |
                            choose(solic) |     | candidato_rechaza
                                          v     |  (opcion rechazada,
                                  ESPERANDO_CANDIDATO     puede elegir otra)
                                          |     |
                              candidato_  |     | reject(admin)
                                acepta    |     v
                                          v   RECHAZADA
                                       APROBADA

Acciones:
    propose            - admin propone 2+ opciones (PENDIENTE -> CON_PROPUESTAS)
    choose             - solicitante elige una opcion (CON_PROPUESTAS -> ESPERANDO_CANDIDATO)
    candidato_acepta   - candidato confirma swap (ESPERANDO_CANDIDATO -> APROBADA)
    candidato_rechaza  - candidato declina swap (ESPERANDO_CANDIDATO -> CON_PROPUESTAS)
    reject             - admin rechaza la solicitud (cualquier no-terminal -> RECHAZADA)

Terminal: APROBADA, RECHAZADA.
"""
from __future__ import annotations

from typing import Optional

from django.core.exceptions import ValidationError

from .models import SolicitudCambio


# ---------------------------------------------------------------------------
# Definicion de transiciones
# ---------------------------------------------------------------------------

# Para cada estado actual, mapea: action -> estado destino
ALLOWED_TRANSITIONS: dict[str, dict[str, str]] = {
    SolicitudCambio.PENDIENTE: {
        "propose": SolicitudCambio.CON_PROPUESTAS,
        "reject":  SolicitudCambio.RECHAZADA,
    },
    SolicitudCambio.CON_PROPUESTAS: {
        # Flujo simplificado: cuando el solicitante elige, el swap se ejecuta
        # inmediatamente en BD. El admin recibe notificacion del resultado.
        "choose":  SolicitudCambio.APROBADA,
        "reject":  SolicitudCambio.RECHAZADA,
    },
    # Estado legacy: solicitudes que se crearon antes del 2026-06-05 y quedaron
    # esperando confirmacion del candidato. Permitimos transicionar manualmente.
    SolicitudCambio.ESPERANDO_CANDIDATO: {
        "candidato_acepta":  SolicitudCambio.APROBADA,
        "candidato_rechaza": SolicitudCambio.CON_PROPUESTAS,
        "reject":            SolicitudCambio.RECHAZADA,
    },
    # Estados terminales: no admiten mas transiciones
    SolicitudCambio.APROBADA:  {},
    SolicitudCambio.RECHAZADA: {},
}

# Quien puede disparar cada accion (rol esperado)
ACTOR_ROLES: dict[str, set[str]] = {
    "propose":           {"admin"},
    "choose":            {"monitor"},   # ademas debe ser el solicitante
    "candidato_acepta":  {"monitor"},   # legacy
    "candidato_rechaza": {"monitor"},   # legacy
    "reject":            {"admin"},
}

# Mensajes de error consistentes
ERROR_MESSAGES = {
    "invalid_transition": (
        "Transicion no permitida: solicitud en estado '{from_state}' "
        "no admite la accion '{action}'."
    ),
    "wrong_actor": (
        "Solo usuarios con rol '{required}' pueden ejecutar la accion '{action}'. "
        "Tu rol es '{got}'."
    ),
    "not_solicitante": (
        "Solo el monitor solicitante puede ejecutar 'choose'."
    ),
    "not_candidato": (
        "Solo el monitor candidato propuesto puede aceptar o rechazar el swap."
    ),
}


# ---------------------------------------------------------------------------
# API publica
# ---------------------------------------------------------------------------

def is_terminal(state: str) -> bool:
    """True si el estado es final (APROBADA o RECHAZADA)."""
    return state in (SolicitudCambio.APROBADA, SolicitudCambio.RECHAZADA)


def next_state(current: str, action: str) -> Optional[str]:
    """Retorna el estado destino para (current, action) o None si invalido."""
    return ALLOWED_TRANSITIONS.get(current, {}).get(action)


def assert_transition(solicitud: SolicitudCambio, action: str, actor=None, candidato_id=None) -> str:
    """Valida que la transicion sea legal y retorna el estado destino.

    Verifica:
    1. El estado actual permite esa accion.
    2. El actor tiene el rol requerido para esa accion.
    3. Para 'choose': el actor es el solicitante.
    4. Para 'candidato_acepta'/'candidato_rechaza': el actor es el candidato
       de la opcion (candidato_id, que debe pasarse explicitamente).

    Args:
        solicitud: La solicitud sobre la que se intenta la accion.
        action: 'propose' | 'choose' | 'candidato_acepta' | 'candidato_rechaza' | 'reject'.
        actor: Usuario que dispara la accion.
        candidato_id: ID del candidato de la opcion elegida (requerido para
            acciones candidato_*).

    Returns:
        El estado destino que tomara la solicitud.

    Raises:
        ValidationError: Si la transicion no es permitida.
    """
    current = solicitud.estado
    target = next_state(current, action)

    if target is None:
        raise ValidationError(
            ERROR_MESSAGES["invalid_transition"].format(
                from_state=current, action=action,
            )
        )

    # Valida el rol del actor
    required_roles = ACTOR_ROLES.get(action, set())
    if actor is not None and required_roles:
        actor_role = getattr(actor, "rol", None)
        if actor_role not in required_roles:
            raise ValidationError(
                ERROR_MESSAGES["wrong_actor"].format(
                    required="' o '".join(sorted(required_roles)),
                    action=action,
                    got=actor_role or "<sin rol>",
                )
            )

    # Para 'choose' verifica que el actor es el solicitante
    if action == "choose" and actor is not None:
        if actor.pk != solicitud.solicitante_id:
            raise ValidationError(ERROR_MESSAGES["not_solicitante"])

    # Para acciones de candidato: verifica que el actor sea ese candidato
    if action in ("candidato_acepta", "candidato_rechaza") and actor is not None:
        if candidato_id is None or actor.pk != candidato_id:
            raise ValidationError(ERROR_MESSAGES["not_candidato"])

    return target


def available_actions(solicitud: SolicitudCambio, actor=None, candidato_id=None) -> list[str]:
    """Lista las acciones que el actor puede ejecutar sobre la solicitud."""
    result: list[str] = []
    for action in ALLOWED_TRANSITIONS.get(solicitud.estado, {}):
        try:
            assert_transition(solicitud, action, actor, candidato_id=candidato_id)
            result.append(action)
        except ValidationError:
            pass
    return result
