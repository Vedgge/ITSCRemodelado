"""Site navigation, expressed once, as data.

The header/nav block was 74 lines copy-pasted into 21 files, and had already
drifted into 6 mutually-inconsistent variants — meaning six different navs were
live simultaneously.  Nine of its links pointed at ``href="#"`` even though the
target pages existed on disk.

Defining it here means a menu change is a one-line edit, and the active-page
highlight (absent from the original) falls out for free.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from flask import request, url_for


@dataclass(frozen=True)
class NavItem:
    label: str
    endpoint: str | None = None
    params: dict[str, object] = field(default_factory=dict)
    children: tuple[NavItem, ...] = ()
    #: Marks sections that have no content yet, so the template can label them
    #: honestly instead of silently linking to a blank page.
    placeholder: bool = False

    def url(self) -> str:
        if not self.endpoint:
            return "#"
        try:
            return url_for(self.endpoint, **self.params)  # type: ignore[arg-type]
        except Exception:
            return "#"

    def is_active(self) -> bool:
        if self.endpoint and request.endpoint == self.endpoint:
            return True
        return any(child.is_active() for child in self.children)


#: The ten tecnicaturas, taken verbatim from the existing nav dropdown.
CARRERAS = (
    "Administración",
    "Bromatología",
    "Desarrollo de Software",
    "Enfermería",
    "Gestión Ambiental",
    "Gestión y Mantenimiento",
    "Higiene y Seguridad",
    "Instrumentación Quirúrgica",
    "Óptica y Contactología",
    "Prótesis Dental",
)


def _carrera_items() -> tuple[NavItem, ...]:
    from itsc.services.slugs import slugify

    return tuple(
        NavItem(label=nombre, endpoint="public.carrera", params={"slug": slugify(nombre)})
        for nombre in CARRERAS
    )


def main_nav() -> tuple[NavItem, ...]:
    return (
        NavItem("Inicio", "public.index"),
        NavItem("Carreras", "public.carreras", children=_carrera_items()),
        NavItem(
            "Estudiantes",
            "public.estudiantes",
            children=(
                NavItem("Exámenes", "public.examenes"),
                NavItem("Egresados", "public.egresados"),
                NavItem("Ser técnico", "public.ser_tecnico"),
            ),
        ),
        NavItem("Novedades", "novedades.list"),
        NavItem("Nosotros", "public.nosotros"),
        NavItem("Contacto", "contacto.form"),
        NavItem(
            "Convocatorias",
            "documentos.list",
            {"categoria": "convocatorias"},
            children=(
                NavItem(
                    "Convocatorias vigentes",
                    "documentos.list",
                    {"categoria": "convocatorias", "vigencia": "vigentes"},
                ),
                NavItem(
                    "Convocatorias no vigentes",
                    "documentos.list",
                    {"categoria": "convocatorias", "vigencia": "no-vigentes"},
                ),
            ),
        ),
        NavItem(
            "Información extra",
            None,
            children=(
                NavItem("Cooperadora", "public.cooperadora"),
                NavItem("Resoluciones", "documentos.list", {"categoria": "resoluciones"}),
                NavItem(
                    "Material para descargar",
                    "documentos.list",
                    {"categoria": "materiales-para-descargar"},
                ),
                NavItem("Actas y dictámenes", "documentos.list", {"categoria": "actas-dictamenes"}),
                NavItem("Preguntas frecuentes", "public.faq"),
            ),
        ),
    )


def footer_nav() -> tuple[NavItem, ...]:
    """The footer previously held three columns of Lorem ipsum."""
    return (
        NavItem("Inicio", "public.index"),
        NavItem("Carreras", "public.carreras"),
        NavItem("Novedades", "novedades.list"),
        NavItem("Preguntas frecuentes", "public.faq"),
        NavItem("Contacto", "contacto.form"),
    )


def nav_context() -> dict[str, object]:
    """Injected into every template by the app factory."""
    return {"main_nav": main_nav(), "footer_nav": footer_nav(), "carreras": CARRERAS}
