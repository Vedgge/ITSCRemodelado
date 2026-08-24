#!/bin/sh
set -eu

# Migrations are NOT run here. A dedicated one-shot `migrate` service owns
# them, so scaling web to two replicas cannot race two `alembic upgrade` runs
# against the same database.

echo "[entrypoint] waiting for postgres..."
i=0
until pg_isready -q -d "${DATABASE_URL#*://}" 2>/dev/null || pg_isready -q -h "${POSTGRES_HOST:-db}" -U "${POSTGRES_USER:-itsc}"; do
    i=$((i + 1))
    if [ "$i" -ge 60 ]; then
        echo "[entrypoint] postgres did not become ready in 60s" >&2
        exit 1
    fi
    sleep 1
done
echo "[entrypoint] postgres ready after ${i}s"

exec "$@"
