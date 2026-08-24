"""Slug generation."""

from __future__ import annotations

import pytest

from itsc.services.slugs import slugify, unique_slug


@pytest.mark.parametrize(
    "value,expected",
    [
        ("ITSC celebra su 10mo aniversario", "itsc-celebra-su-10mo-aniversario"),
        ("Prótesis Dental", "protesis-dental"),
        ("Óptica y Contactología", "optica-y-contactologia"),
        ("Instrumentación Quirúrgica", "instrumentacion-quirurgica"),
        ("  espacios   colapsados  ", "espacios-colapsados"),
        ("Símbolos !@#$%^&*() raros", "simbolos-raros"),
        ("Resolución N° 123/2024", "resolucion-n-123-2024"),
        ("MAYÚSCULAS", "mayusculas"),
        ("---guiones---", "guiones"),
    ],
)
def test_slugify(value, expected):
    assert slugify(value) == expected


def test_slugify_is_idempotent():
    once = slugify("Especialización para Enfermeros")
    assert slugify(once) == once


def test_slugify_truncates_on_a_word_boundary():
    slug = slugify("palabra " * 60, max_length=50)
    assert len(slug) <= 50
    assert not slug.endswith("-")
    assert "palabra" in slug


def test_slugify_of_only_symbols_is_empty():
    assert slugify("!!!") == ""


def test_unique_slug_appends_a_suffix_on_collision():
    taken = {"una-novedad", "una-novedad-2"}
    assert unique_slug("Una novedad", lambda s: s in taken) == "una-novedad-3"


def test_unique_slug_returns_base_when_free():
    assert unique_slug("Una novedad", lambda s: False) == "una-novedad"


def test_unique_slug_falls_back_for_symbol_only_input():
    assert unique_slug("!!!", lambda s: False) == "item"


def test_unique_slug_respects_max_length_with_suffix():
    taken = {"a" * 20}
    result = unique_slug("a" * 40, lambda s: s in taken, max_length=20)
    assert len(result) <= 20
    assert result not in taken
