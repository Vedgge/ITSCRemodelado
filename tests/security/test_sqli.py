"""SQL injection regressions.

Guards `main.py:66-71` and `main.py:89`, which built queries by f-string
interpolation:

    self.cursor.execute(f"SELECT * FROM novedades WHERE codigo = {codigo}")
    self.cursor.execute(f"DELETE FROM novedades WHERE codigo = {codigo}")

The first was reachable *unauthenticated* through POST /novedades, which read
`codigo` straight from request.form -- and CORS(app) let any origin call it.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src"

PAYLOADS = [
    "1 OR 1=1",
    "' OR '1'='1",
    "1; DROP TABLE novedades--",
    "1 UNION SELECT password_hash FROM users--",
    "%27%20OR%201=1",
    "1'); DELETE FROM novedades; --",
    "\\'; DROP TABLE users; --",
]


@pytest.mark.security
@pytest.mark.parametrize("payload", PAYLOADS)
def test_slug_lookup_rejects_sqli(client, novedad, payload):
    """A payload in the slug must 404, never 200-with-data and never 500."""
    response = client.get(f"/novedades/{payload}")
    assert response.status_code in (301, 308, 404), (
        f"payload {payload!r} produced {response.status_code}"
    )


@pytest.mark.security
@pytest.mark.parametrize("payload", PAYLOADS)
def test_search_rejects_sqli(client, novedad, payload):
    """Search feeds user text to to_tsquery territory; it must stay data.

    plainto_tsquery is used rather than to_tsquery precisely so operator
    characters are treated as literal words instead of query syntax.
    """
    response = client.get("/buscar", query_string={"q": payload})
    assert response.status_code == 200


@pytest.mark.security
def test_sqli_does_not_destroy_data(client, db, novedad):
    """The direct regression for the f-string DELETE at main.py:89."""
    from itsc.models import Novedad

    before = db.session.query(Novedad).count()
    assert before >= 1

    for payload in ("1; DROP TABLE novedades--", "1 OR 1=1"):
        client.get(f"/novedades/{payload}")
        client.get("/buscar", query_string={"q": payload})

    assert db.session.query(Novedad).count() == before


@pytest.mark.security
def test_api_pagination_params_are_not_injectable(client, novedad):
    for param in ("page", "per_page"):
        response = client.get(
            "/api/v1/novedades", query_string={param: "1; DROP TABLE novedades--"}
        )
        assert response.status_code == 200
        # Non-integer input falls back to the default rather than reaching SQL.
        assert response.get_json()["meta"]["page"] >= 1


@pytest.mark.security
def test_no_string_formatted_sql_in_source():
    """Static guard: fail the build if f-string SQL is ever reintroduced.

    This is the test that stops the original vulnerability from coming back in
    a future refactor, rather than merely proving today's code is clean.
    """
    offenders: list[str] = []

    for path in SRC.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if name not in {"execute", "executemany", "text"}:
                continue
            if not node.args:
                continue
            first = node.args[0]
            is_interpolated = (
                isinstance(first, ast.JoinedStr)
                or (isinstance(first, ast.BinOp) and isinstance(first.op, ast.Mod))
                or (
                    isinstance(first, ast.Call)
                    and isinstance(first.func, ast.Attribute)
                    and first.func.attr == "format"
                )
            )
            if is_interpolated:
                offenders.append(f"{path.relative_to(SRC)}:{node.lineno}")

    assert not offenders, "string-formatted SQL found at: " + ", ".join(offenders)
