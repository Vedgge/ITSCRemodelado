"""Custom Flask CLI commands."""

from __future__ import annotations

import secrets
import sys
from datetime import UTC, date, datetime, timedelta

import click
from flask.cli import AppGroup

from itsc.extensions import db

itsc_cli = AppGroup("itsc", help="ITSC maintenance commands.")

#: Rejected outright regardless of length.
COMMON_PASSWORDS = frozenset(
    {
        "password",
        "password123",
        "12345678",
        "123456789",
        "qwertyuiop",
        "administrador",
        "contrasena",
        "itsc1234",
        "admin1234",
        "letmein123",
    }
)
MIN_PASSWORD_LENGTH = 12


def _validate_password(password: str) -> list[str]:
    problems = []
    if len(password) < MIN_PASSWORD_LENGTH:
        problems.append(f"debe tener al menos {MIN_PASSWORD_LENGTH} caracteres")
    if password.lower() in COMMON_PASSWORDS:
        problems.append("es una contraseña demasiado común")
    if password.isdigit():
        problems.append("no puede ser solo números")
    return problems


@itsc_cli.command("create-admin")
@click.option("--username", prompt=True, help="Nombre de usuario.")
@click.option("--email", default=None, help="Email (opcional).")
@click.option("--role", type=click.Choice(["admin", "editor"]), default="admin")
@click.option(
    "--password-stdin",
    is_flag=True,
    help="Leer la contraseña desde stdin (para provisioning automatizado).",
)
def create_admin(username: str, email: str | None, role: str, password_stdin: bool) -> None:
    """Create an administrative user.

    The password is never accepted as a command-line argument: argv is visible
    in shell history and in the process table to every other user on the host.

    Interactively it is prompted for with echo disabled. For automated
    provisioning, --password-stdin reads a single line from stdin, the same
    pattern `docker login --password-stdin` uses:

        printf '%s' "$ADMIN_PASSWORD" | flask itsc create-admin \
            --username admin --password-stdin
    """
    from itsc.models import User

    if db.session.query(User).filter(User.username == username).first():
        click.secho(f"El usuario {username!r} ya existe.", fg="red")
        sys.exit(1)

    if password_stdin:
        password = sys.stdin.readline().rstrip("\n")
        if not password:
            click.secho("No se recibió ninguna contraseña por stdin.", fg="red")
            sys.exit(1)
    else:
        password = click.prompt("Contraseña", hide_input=True, confirmation_prompt=True)
    if problems := _validate_password(password):
        click.secho("Contraseña rechazada: " + "; ".join(problems), fg="red")
        sys.exit(1)

    user = User(username=username, email=email or None, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    click.secho(f"Usuario {username!r} creado con rol {role!r}.", fg="green")


@itsc_cli.command("seed-categories")
def seed_categories() -> None:
    """Insert the four document categories. Idempotent."""
    from itsc.models import DocumentCategory

    rows = [
        {
            "slug": "convocatorias",
            "nombre": "Convocatorias",
            "descripcion": "Llamados a inscripción, concursos y coberturas de cargos.",
            "icon": "megaphone",
            "orden": 1,
            "has_vigencia": True,
        },
        {
            "slug": "resoluciones",
            "nombre": "Resoluciones",
            "descripcion": "Resoluciones institucionales publicadas por el instituto.",
            "icon": "gavel",
            "orden": 2,
            "has_vigencia": False,
        },
        {
            "slug": "actas-dictamenes",
            "nombre": "Actas y dictámenes",
            "descripcion": "Actas de reuniones y dictámenes de las comisiones evaluadoras.",
            "icon": "clipboard",
            "orden": 3,
            "has_vigencia": False,
        },
        {
            "slug": "mesas-de-examen",
            "nombre": "Mesas de examen",
            "descripcion": "Cronogramas de mesas de examen publicados por el instituto.",
            "icon": "calendar",
            "orden": 5,
            "has_vigencia": True,
        },
        {
            "slug": "materiales-para-descargar",
            "nombre": "Material para descargar",
            "descripcion": "Formularios, instructivos y material de consulta.",
            "icon": "download",
            "orden": 4,
            "has_vigencia": False,
        },
    ]
    created = 0
    for row in rows:
        existing = db.session.query(DocumentCategory).filter_by(slug=row["slug"]).first()
        if existing:
            for key, value in row.items():
                setattr(existing, key, value)
        else:
            db.session.add(DocumentCategory(**row))
            created += 1
    db.session.commit()
    click.secho(
        f"Categorías listas ({created} nuevas, {len(rows) - created} actualizadas).", fg="green"
    )


@itsc_cli.command("seed-demo")
@click.option("--force", is_flag=True, help="Seed even if content already exists.")
def seed_demo(force: bool) -> None:
    """Insert clearly-labelled sample content.

    Every seeded row is prefixed "[Contenido de muestra]". This project has no
    access to ITSC's real resolutions, exam dates or fees, and inventing them
    would put actionable falsehoods on a public site.
    """
    from itsc.models import Document, DocumentCategory, Novedad
    from itsc.models.novedad import STATUS_PUBLISHED
    from itsc.services.slugs import unique_slug

    if not force and db.session.query(Novedad).count():
        click.secho("Ya hay contenido. Usá --force para sembrar igualmente.", fg="yellow")
        return

    now = datetime.now(UTC)
    samples = [
        (
            "ITSC celebra su 10mo aniversario",
            "Una década formando técnicos y técnicas superiores en Córdoba.",
        ),
        (
            "Especialización para enfermeros",
            "Nueva propuesta de formación continua para egresados de Enfermería.",
        ),
        (
            "Prácticas profesionalizantes en DENSO S.A.",
            "Estudiantes de carreras técnicas visitaron la planta industrial.",
        ),
    ]
    for i, (titulo, resumen) in enumerate(samples):
        marked = f"[Contenido de muestra] {titulo}"
        slug = unique_slug(
            marked,
            lambda s: db.session.query(Novedad).filter_by(slug=s).first() is not None,
        )
        db.session.add(
            Novedad(
                slug=slug,
                titulo=marked,
                resumen=resumen,
                cuerpo=(
                    f"{resumen}\n\n"
                    "**Este es contenido de muestra**, incluido únicamente para "
                    "demostrar el funcionamiento del sistema de novedades. "
                    "No corresponde a una publicación oficial del ITSC."
                ),
                status=STATUS_PUBLISHED,
                published_at=now - timedelta(days=i * 7),
            )
        )

    convocatorias = db.session.query(DocumentCategory).filter_by(slug="convocatorias").first()
    if convocatorias:
        db.session.add(
            Document(
                category=convocatorias,
                slug="ejemplo-de-convocatoria",
                titulo="[Contenido de muestra] Convocatoria de ejemplo",
                descripcion=(
                    "Registro de ejemplo para demostrar el listado de convocatorias "
                    "y el filtro de vigencia. No es una convocatoria real."
                ),
                fecha_documento=date.today(),  # noqa: DTZ011
                vigente_hasta=date.today() + timedelta(days=30),  # noqa: DTZ011
                status=STATUS_PUBLISHED,
                published_at=now,
            )
        )

    db.session.commit()
    click.secho("Contenido de muestra creado (visiblemente etiquetado).", fg="green")


@itsc_cli.command("purge-contact")
@click.option("--days", default=None, type=int, help="Override the retention window.")
@click.option("--dry-run", is_flag=True)
def purge_contact(days: int | None, dry_run: bool) -> None:
    """Delete contact messages past the retention window (personal data)."""
    from flask import current_app

    from itsc.models import ContactMessage

    window = days or current_app.config["CONTACT_RETENTION_DAYS"]
    cutoff = datetime.now(UTC) - timedelta(days=window)
    query = db.session.query(ContactMessage).filter(ContactMessage.created_at < cutoff)
    count = query.count()
    if dry_run:
        click.echo(f"[dry-run] Se eliminarían {count} mensajes anteriores a {cutoff.date()}.")
        return
    query.delete(synchronize_session=False)
    db.session.commit()
    click.secho(f"{count} mensajes eliminados (anteriores a {cutoff.date()}).", fg="green")


@itsc_cli.command("gen-secret")
def gen_secret() -> None:
    """Print a cryptographically strong secret for SECRET_KEY / IP_HASH_PEPPER."""
    click.echo(secrets.token_urlsafe(64))
