# syntax=docker/dockerfile:1.7
# ---------------------------------------------------------------------------
# Multi-stage: compilers exist only in the builder, never in the shipped image.
# ---------------------------------------------------------------------------
FROM python:3.14-slim-bookworm AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements/base.txt /tmp/base.txt
# --require-hashes: a compromised mirror cannot substitute a package.
RUN pip install --require-hashes -r /tmp/base.txt

COPY pyproject.toml README.md /build/
COPY src /build/src
RUN pip install --no-deps /build


# ---------------------------------------------------------------------------
FROM python:3.14-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    FLASK_APP="itsc:create_app"

# libpq5 only (the client library), not libpq-dev; no compilers in the image.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 postgresql-client curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 10001 --create-home --shell /usr/sbin/nologin itsc

COPY --from=builder /opt/venv /opt/venv
COPY --chown=itsc:itsc migrations /srv/app/migrations
COPY --chown=itsc:itsc docker/web/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY --chown=itsc:itsc docker/web/gunicorn.conf.py /srv/app/gunicorn.conf.py
RUN chmod +x /usr/local/bin/entrypoint.sh

WORKDIR /srv/app
# Uploads live on a volume mounted here, outside the static tree.
RUN mkdir -p /srv/uploads && chown itsc:itsc /srv/uploads

USER 10001

# Liveness only: deliberately does not touch the database, so a brief DB
# outage cannot restart-loop every container.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/healthz || exit 1

EXPOSE 8000
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["gunicorn", "-c", "/srv/app/gunicorn.conf.py", "itsc:create_app()"]
