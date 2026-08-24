"""Markdown rendering with a strict sanitisation allowlist.

This is the ONLY place in the codebase where HTML bypasses Jinja's
autoescaping. A test asserts that ``|safe`` appears nowhere else in the
template tree, so this function is the single audited boundary.
"""

from __future__ import annotations

import markdown as md
import nh3
from markupsafe import Markup

#: Everything not listed is stripped. Note the absence of script, iframe,
#: object, embed, form, style and svg.
ALLOWED_TAGS = {
    "p", "br", "hr",
    "strong", "b", "em", "i", "u", "s", "sub", "sup",
    "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li",
    "blockquote", "code", "pre",
    "a", "img",
    "table", "thead", "tbody", "tr", "th", "td",
}
ALLOWED_ATTRIBUTES = {
    # "rel" is deliberately absent: nh3 sets it itself via link_rel below,
    # and passing both raises. "target" is dropped for the same reason --
    # target=_blank without rel=noopener is a tabnabbing vector.
    "a": {"href", "title"},
    "img": {"src", "alt", "title", "width", "height", "loading"},
    "th": {"colspan", "rowspan", "scope"},
    "td": {"colspan", "rowspan"},
}
#: Anything else — javascript:, data:, vbscript: — is dropped.
ALLOWED_SCHEMES = {"http", "https", "mailto", "tel"}


def render_markdown(text: str | None) -> Markup:
    """Render *text* to sanitised HTML safe for direct insertion."""
    if not text:
        return Markup("")

    html = md.markdown(
        text,
        extensions=["extra", "sane_lists", "nl2br"],
        output_format="html",
    )
    clean = nh3.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes={k: set(v) for k, v in ALLOWED_ATTRIBUTES.items()},
        url_schemes=ALLOWED_SCHEMES,
        link_rel="noopener noreferrer",
        strip_comments=True,
    )
    return Markup(clean)  # noqa: S704 - nh3.clean output is the audited boundary


def excerpt(text: str | None, length: int = 200) -> str:
    """Plain-text excerpt, with all markup removed."""
    if not text:
        return ""
    plain = nh3.clean(md.markdown(text), tags=set()).strip()
    if len(plain) <= length:
        return plain
    return plain[:length].rsplit(" ", 1)[0] + "…"
