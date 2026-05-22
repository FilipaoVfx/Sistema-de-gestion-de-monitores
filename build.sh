#!/usr/bin/env bash
# Script de build para Render
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate
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
