"""URL slug generation.

Accent-stripping matters here: "Prótesis Dental" and "Óptica y Contactología"
must become ASCII paths, and the original repo already demonstrated the failure
mode with filenames like "especializacion enfermeros-2.jpg" that required
URL-encoding everywhere they appeared.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable

MAX_SLUG_LENGTH = 180
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def slugify(value: str, *, max_length: int = MAX_SLUG_LENGTH) -> str:
    """``'ITSC celebra su 10mo aniversario'`` -> ``'itsc-celebra-su-10mo-aniversario'``."""
    # NFKD splits "ó" into "o" + combining accent; encoding to ASCII drops the accent.
    normalised = unicodedata.normalize("NFKD", value)
    ascii_only = normalised.encode("ascii", "ignore").decode("ascii")
    slug = _NON_ALNUM.sub("-", ascii_only.lower()).strip("-")

    if len(slug) > max_length:
        # Truncate on a word boundary so slugs stay readable.
        slug = slug[:max_length].rsplit("-", 1)[0] or slug[:max_length]
    return slug.strip("-")


def unique_slug(
    value: str,
    exists: Callable[[str], bool],
    *,
    max_length: int = MAX_SLUG_LENGTH,
) -> str:
    """Slugify *value*, appending ``-2``, ``-3``... until ``exists`` is False."""
    base = slugify(value, max_length=max_length) or "item"
    if not exists(base):
        return base

    suffix = 2
    while True:
        tail = f"-{suffix}"
        candidate = f"{base[: max_length - len(tail)].rstrip('-')}{tail}"
        if not exists(candidate):
            return candidate
        suffix += 1
        if suffix > 1000:  # pragma: no cover - pathological
            raise RuntimeError(f"could not find a unique slug for {value!r}")
