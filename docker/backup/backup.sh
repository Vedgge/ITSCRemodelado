#!/bin/sh
# Nightly backup of the database and the uploads volume.
#
# A backup you have never restored is not a backup. `make restore-drill`
# exercises the restore path against a throwaway stack; run it on a schedule,
# not just after an incident.
set -eu

STAMP="$(date +%Y%m%d-%H%M%S)"
DEST="/backups"
RETENTION="${BACKUP_RETENTION_DAYS:-7}"
mkdir -p "$DEST"

export PGPASSWORD="$POSTGRES_PASSWORD"

echo "[backup] $STAMP dumping database..."
# -Fc (custom format) supports selective restore and compresses.
pg_dump -h db -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc \
        -f "$DEST/db-$STAMP.dump"

echo "[backup] $STAMP archiving uploads..."
# Uploads cannot be regenerated from source; the database alone is not enough
# to restore the site.
tar -czf "$DEST/uploads-$STAMP.tar.gz" -C /srv uploads

echo "[backup] pruning backups older than ${RETENTION} days..."
find "$DEST" -name 'db-*.dump'        -mtime "+$RETENTION" -delete
find "$DEST" -name 'uploads-*.tar.gz' -mtime "+$RETENTION" -delete

echo "[backup] $STAMP done:"
ls -lh "$DEST" | tail -5
