#!/usr/bin/env bash
# Script de build para Render
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

# WIPE opcional: si DEMO_WIPE=1, borra TODOS los datos de demo
# (asignaciones, solicitudes, monitores, salas, horarios, semestres).
# Preserva admins. Util para resetear BD desordenada antes del seed.
# Recuerda QUITAR la env var despues del deploy para que no se repita.
if [ "${DEMO_WIPE:-}" = "1" ]; then
  echo "==> DEMO_WIPE=1: limpiando BD antes del seed"
  python manage.py wipe_demo
fi

python manage.py seed_demo

# Admin extra opcional: si las env vars EXTRA_ADMIN_EMAIL y EXTRA_ADMIN_PASSWORD
# estan definidas en Render, crea/actualiza ese admin de forma idempotente.
if [ -n "${EXTRA_ADMIN_EMAIL:-}" ] && [ -n "${EXTRA_ADMIN_PASSWORD:-}" ]; then
  python manage.py create_admin \
    --email "$EXTRA_ADMIN_EMAIL" \
    --password "$EXTRA_ADMIN_PASSWORD" \
    --first-name "${EXTRA_ADMIN_FIRST_NAME:-Admin}" \
    --last-name  "${EXTRA_ADMIN_LAST_NAME:-Sistema}"
fi
