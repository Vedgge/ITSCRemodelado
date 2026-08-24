# ITSC Remodelado

A production-grade rebuild of the Instituto Técnico Superior Córdoba website.

> **Proyecto de portafolio.** This is a personal reconstruction for educational
> purposes and is **not affiliated with, endorsed by, or operated by** the ITSC.
> The official site is <https://www.institutotecnicocordoba.com>. Every
> deployment carries a visible disclaimer and serves `noindex` plus a
> `Disallow: /` robots policy, so it can never be mistaken for the real site in
> search results.

The project began in October 2023 as a front-end exercise. This rewrite turns it
into software that can actually be exposed to the internet.

---

## What it is

A server-rendered Flask application with an authenticated admin panel, backed by
PostgreSQL and deployed with Docker.

- **Public site** — institutional pages, news with slug URLs and an RSS feed,
  five document repositories (convocatorias, resoluciones, actas y dictámenes,
  material para descargar, mesas de examen), full-text search, and a contact form.
- **Admin panel** — session auth with argon2id, CSRF on every mutation, image
  and PDF upload with server-side re-encoding, and a contact inbox.
- **Read-only JSON API** at `/api/v1/novedades`, paginated and explicitly
  serialised.

## Stack

| Layer | Choice |
|---|---|
| Web | Flask 3.1, Jinja2, gunicorn (gthread) |
| Data | PostgreSQL 16, SQLAlchemy 2.0 (typed), Alembic |
| Sessions & limits | Redis 7 |
| Auth | Flask-Login, argon2id, Flask-WTF (CSRF) |
| Security | Flask-Talisman (strict CSP), Flask-Limiter, nh3, Pillow |
| Ops | Docker Compose, nginx, structlog, GitHub Actions |

No jQuery, no Bootstrap, no CDN. Every asset — fonts, icons, CSS, JS — is
self-hosted, which is what makes a `script-src 'self'` policy with no
`unsafe-inline` achievable.

---

## Quick start

Requires Docker and Docker Compose.

```bash
cp .env.example .env
# Generate the two secrets the app refuses to start without:
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(64))"
python3 -c "import secrets; print('IP_HASH_PEPPER=' + secrets.token_urlsafe(64))"
# ...and set POSTGRES_PASSWORD / REDIS_PASSWORD in .env

docker compose up -d --build
docker compose exec web flask itsc seed-categories
docker compose exec -it web flask itsc create-admin --username admin
```

Then open <http://localhost:8000>. The admin panel is at `/admin`.

For automated provisioning, the password can come from stdin instead of a
prompt — it is never accepted as an argument, where it would land in shell
history and the process table:

```bash
printf '%s' "$ADMIN_PASSWORD" | docker compose exec -T web \
    flask itsc create-admin --username admin --password-stdin
```

### Local development without Docker

```bash
make install          # venv + hash-verified dependencies
make migrate
make admin
make test
```

`make help` lists everything.

---

## Verification

```bash
make check                       # lint, types, tests, security scan
./scripts/smoke.sh http://localhost:8000   # 40 end-to-end checks
```

The test suite runs against a **real PostgreSQL**, never SQLite — SQLite would
silently skip `CITEXT`, generated `TSVECTOR` columns, partial unique indexes and
`ON DELETE RESTRICT`, so a green run would prove very little. The schema is
built by running the migrations, which makes every test run a migration test.
CSRF stays **enabled** in tests; suites that disable it are how CSRF regressions
reach production.

305 tests, 92% coverage. Several are static guards that stop a class of bug from
returning rather than merely detecting today's absence of it:

- an AST scan rejecting f-string/`%`/`.format()` SQL anywhere in `src/`
- an AST scan rejecting literal credentials passed to `password=` arguments
- a `url_map` sweep asserting every admin and non-`GET` route rejects anonymous
  access, so newly added routes are covered automatically
- a template scan rejecting inline `<script>`, `style=` and `<style>`, which is
  what keeps the strict CSP from rotting
- a template scan confining `|safe` to the single audited sanitised-body line
- a scan rejecting hardcoded `127.0.0.1` / `localhost` in templates and JS

---

## Architecture notes

**Server-side rendering, deliberately.** The previous version fetched news as
JSON and built cards by concatenating database values into `innerHTML` in four
near-identical loops. Rendering in Jinja eliminates that XSS class structurally
rather than by discipline: there is no code path where a developer *can* forget
to escape. It also removed the reason seven copies of
`const URL = "http://127.0.0.1:5000/"` existed.

**Uploads are re-encoded, not just validated.** Extension and MIME checks are
bypassable — a polyglot file is a valid JPEG *and* valid HTML. Decoding to a
pixel buffer and re-encoding as WebP is not survivable by a polyglot, and it
strips EXIF (including GPS) in the same step. Uploads are stored outside
`static/` under a server-generated UUID, so path traversal is structurally
impossible rather than filtered.

**Vigencia is derived, never stored.** Whether a convocatoria is open is
computed from its dates in SQL, which is what collapses two separately
maintained pages into two filters over one table that cannot disagree.

**Authorisation is a blueprint `before_request`, not a per-view decorator.** A
newly added admin view is protected by default; forgetting a decorator cannot
open a hole.

**Two health endpoints, and the distinction matters.** `/healthz` is liveness
and touches nothing — if it checked the database, a brief outage would
restart-loop every container and turn a five-second blip into a full one.
`/readyz` checks the database, Redis and the upload directory, and reports the
current migration revision.

---

## Content policy

Content here is grounded in facts the project already contained: the address and
phone from the site footer, the ten career names from the navigation, six
captioned fotogalería events, and seven substantive FAQ answers that had already
been written.

Nothing that could mislead a prospective student is invented. Exam dates,
resolution numbers, the cooperadora's fee, staff names and curricula are not
available to this project, so those pages ship as **working, admin-managed
features with honest empty states** rather than with fabricated entries. A
student who acts on a made-up exam date suffers a real harm; an empty section
costs nothing. Demo content is visibly labelled `[Contenido de muestra]`.

---

## Project layout

```
src/itsc/            application package (create_app factory only)
  blueprints/        public, novedades, documentos, contacto, auth, admin, api
  models/            users, media, novedades, documents, contact
  services/          media, slugs, rendering, mail, queries
  templates/         base.html + partials + macros + pages
  static/            css, js, self-hosted fonts, SVG sprite, images
migrations/          Alembic
tests/               unit, integration, security
docker/              web image, nginx, backup
scripts/             optimize_images.py, smoke.sh
```

## Operations

| Task | Command |
|---|---|
| Apply migrations | `make migrate` |
| Create an admin | `make admin` |
| Seed categories | `flask itsc seed-categories` |
| Purge expired contact data | `flask itsc purge-contact` |
| Regenerate image derivatives | `make images` |
| Tail logs | `make logs` |

Contact messages contain personal data and are deleted after
`CONTACT_RETENTION_DAYS` (default 730) by `flask itsc purge-contact`; run it on
a schedule. Nightly backups cover the database and the uploads volume — and a
backup you have never restored is not a backup, so exercise the restore path.

## Licence

MIT for the code. The ITSC name, logo and photographs belong to the institution
and are used here only to reconstruct their site for a portfolio.
