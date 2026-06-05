"""Maquina de estados para SolicitudCambio.

Define las transiciones permitidas, quien puede dispararlas y los invariantes
del estado de la solicitud. Aisla esa logica del servicio para que sea facil
auditar y testear.

Estados:
    PENDIENTE        - recien creada por el monitor solicitante
    CON_PROPUESTAS   - el admin ha propuesto >=2 opciones de swap
    APROBADA         - el monitor eligio una opcion y el swap fue ejecutado
    RECHAZADA        - el admin rechazo la solicitud (terminal)

Transiciones permitidas:

                        +-----------------------+
                        |        PENDIENTE      |
                        +-----------------------+
                         |          |        |
            propose_opts |          |        | reject
                         v          |        |
                +------------------+|        |
                |  CON_PROPUESTAS  ||        |
                +------------------+|        |
                  |         |       |        |
            choose|         |       |        |
                  v         | reject|        |
                +-------+   v       v        v
                |APROBADA|  +-------------------+
                +-------+   |     RECHAZADA     |
                            +-------------------+

Terminal: APROBADA, RECHAZADA.
"""
from __future__ import annotations

from typing import Iterable, Optional

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
        "choose":  SolicitudCambio.APROBADA,
        "reject":  SolicitudCambio.RECHAZADA,
    },
    # Estados terminales: no admiten mas transiciones
    SolicitudCambio.APROBADA:  {},
    SolicitudCambio.RECHAZADA: {},
}

# Quien puede disparar cada accion (rol esperado)
ACTOR_ROLES: dict[str, set[str]] = {
    "propose": {"admin"},
    "choose":  {"monitor"},   # ademas debe ser el solicitante
    "reject":  {"admin"},
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


def assert_transition(solicitud: SolicitudCambio, action: str, actor=None) -> str:
    """Valida que la transicion sea legal y retorna el estado destino.

    Verifica:
    1. El estado actual permite esa accion.
    2. El actor tiene el rol requerido para esa accion.
    3. Para 'choose': el actor es el solicitante.

    Args:
        solicitud: La solicitud sobre la que se intenta la accion.
        action: 'propose' | 'choose' | 'reject'.
        actor: Usuario que dispara la accion.

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

    return target


def available_actions(solicitud: SolicitudCambio, actor=None) -> list[str]:
    """Lista las acciones que el actor puede ejecutar sobre la solicitud."""
    result: list[str] = []
    for action in ALLOWED_TRANSITIONS.get(solicitud.estado, {}):
        try:
            assert_transition(solicitud, action, actor)
            result.append(action)
        except ValidationError:
            pass
    return result
