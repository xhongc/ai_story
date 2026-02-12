#!/bin/sh
set -e

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
  python /app/backend/manage.py migrate --noinput
fi

exec "$@"
