"""CLI commands."""

from __future__ import annotations

import pytest

from itsc.models import ContactMessage, DocumentCategory, Novedad, User


@pytest.fixture
def runner(app, db):
    return app.test_cli_runner()


def test_create_admin(runner, db):
    result = runner.invoke(
        args=["itsc", "create-admin", "--username", "nuevo"],
        input="Una-Clave-Larga-2026\nUna-Clave-Larga-2026\n",
    )
    assert result.exit_code == 0, result.output
    user = db.session.query(User).filter_by(username="nuevo").one()
    assert user.role == "admin"
    assert user.password_hash.startswith("$argon2id$")


def test_create_admin_with_editor_role(runner, db):
    runner.invoke(
        args=["itsc", "create-admin", "--username", "edi", "--role", "editor"],
        input="Una-Clave-Larga-2026\nUna-Clave-Larga-2026\n",
    )
    assert db.session.query(User).filter_by(username="edi").one().role == "editor"


@pytest.mark.parametrize(
    "password,reason",
    [("corta", "12 caracteres"), ("password123", "común"), ("123456789012", "números")],
)
def test_create_admin_rejects_weak_passwords(runner, db, password, reason):
    result = runner.invoke(
        args=["itsc", "create-admin", "--username", "debil"],
        input=f"{password}\n{password}\n",
    )
    assert result.exit_code == 1
    assert reason in result.output
    assert db.session.query(User).filter_by(username="debil").count() == 0


def test_create_admin_rejects_duplicate_username(runner, db, admin_user):
    result = runner.invoke(
        args=["itsc", "create-admin", "--username", "admin_test"],
        input="Una-Clave-Larga-2026\nUna-Clave-Larga-2026\n",
    )
    assert result.exit_code == 1
    assert "ya existe" in result.output


def test_seed_categories_is_idempotent(runner, db):
    first = runner.invoke(args=["itsc", "seed-categories"])
    assert first.exit_code == 0
    count = db.session.query(DocumentCategory).count()
    assert count >= 5

    second = runner.invoke(args=["itsc", "seed-categories"])
    assert second.exit_code == 0
    assert db.session.query(DocumentCategory).count() == count, "reseeding duplicated rows"


def test_seed_demo_labels_everything_as_sample(runner, db):
    runner.invoke(args=["itsc", "seed-categories"])
    result = runner.invoke(args=["itsc", "seed-demo"])
    assert result.exit_code == 0

    items = db.session.query(Novedad).all()
    assert items
    for item in items:
        assert item.titulo.startswith("[Contenido de muestra]"), (
            "seeded content must be visibly labelled; this project has no real "
            "ITSC content and unlabelled samples would read as genuine"
        )


def test_seed_demo_refuses_to_run_twice_without_force(runner, db):
    runner.invoke(args=["itsc", "seed-categories"])
    runner.invoke(args=["itsc", "seed-demo"])
    before = db.session.query(Novedad).count()
    result = runner.invoke(args=["itsc", "seed-demo"])
    assert "Ya hay contenido" in result.output
    assert db.session.query(Novedad).count() == before


def test_purge_contact_dry_run_deletes_nothing(runner, db):
    from datetime import UTC, datetime, timedelta

    old = ContactMessage(
        asunto="Vieja",
        nombre="X",
        email="x@y.co",
        motivo="Otro",
        mensaje="m" * 20,
    )
    db.session.add(old)
    db.session.commit()
    db.session.execute(
        db.text("UPDATE contact_messages SET created_at = :ts"),
        {"ts": datetime.now(UTC) - timedelta(days=5000)},
    )
    db.session.commit()

    result = runner.invoke(args=["itsc", "purge-contact", "--dry-run"])
    assert "Se eliminarían 1" in result.output
    assert db.session.query(ContactMessage).count() == 1


def test_purge_contact_removes_expired_personal_data(runner, db):
    from datetime import UTC, datetime, timedelta

    db.session.add(
        ContactMessage(asunto="Vieja", nombre="X", email="x@y.co", motivo="Otro", mensaje="m" * 20)
    )
    db.session.commit()
    db.session.execute(
        db.text("UPDATE contact_messages SET created_at = :ts"),
        {"ts": datetime.now(UTC) - timedelta(days=5000)},
    )
    db.session.commit()

    result = runner.invoke(args=["itsc", "purge-contact"])
    assert result.exit_code == 0
    assert db.session.query(ContactMessage).count() == 0


def test_purge_contact_keeps_recent_messages(runner, db):
    db.session.add(
        ContactMessage(asunto="Nueva", nombre="X", email="x@y.co", motivo="Otro", mensaje="m" * 20)
    )
    db.session.commit()
    runner.invoke(args=["itsc", "purge-contact"])
    assert db.session.query(ContactMessage).count() == 1


def test_gen_secret_is_long_and_random(runner):
    first = runner.invoke(args=["itsc", "gen-secret"]).output.strip()
    second = runner.invoke(args=["itsc", "gen-secret"]).output.strip()
    assert len(first) >= 64
    assert first != second
