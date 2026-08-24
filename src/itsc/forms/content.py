"""Admin content forms."""

from __future__ import annotations

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import (
    DateField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, Optional

from itsc.models.novedad import STATUSES

STATUS_LABELS = {
    "draft": "Borrador",
    "published": "Publicada",
    "archived": "Archivada",
}


class NovedadForm(FlaskForm):
    titulo = StringField(
        "Título", validators=[DataRequired("El título es obligatorio."), Length(min=3, max=200)]
    )
    resumen = TextAreaField(
        "Resumen",
        validators=[DataRequired("Escribí un resumen breve."), Length(min=10, max=400)],
        description="Se muestra en las tarjetas del listado y como descripción para buscadores.",
    )
    cuerpo = TextAreaField(
        "Cuerpo",
        validators=[DataRequired("El cuerpo no puede estar vacío.")],
        description="Admite Markdown. El HTML se sanitiza antes de mostrarse.",
    )
    imagen = FileField(
        "Imagen",
        validators=[
            Optional(),
            FileAllowed(["jpg", "jpeg", "png", "webp"], "Solo JPG, PNG o WebP."),
        ],
        description="Opcional. Se reescala y convierte a WebP automáticamente.",
    )
    imagen_alt = StringField(
        "Texto alternativo de la imagen",
        validators=[Optional(), Length(max=255)],
        description="Describí la imagen para quienes usan lectores de pantalla.",
    )
    status = SelectField(
        "Estado", choices=[(s, STATUS_LABELS[s]) for s in STATUSES], default="draft"
    )
    submit = SubmitField("Guardar")


class DocumentForm(FlaskForm):
    titulo = StringField(
        "Título", validators=[DataRequired("El título es obligatorio."), Length(min=3, max=300)]
    )
    numero = StringField(
        "Número", validators=[Optional(), Length(max=60)],
        description='Por ejemplo "123/2024". Opcional.',
    )
    descripcion = TextAreaField("Descripción", validators=[Optional(), Length(max=5000)])
    fecha_documento = DateField(
        "Fecha del documento", validators=[DataRequired("Indicá la fecha del documento.")]
    )
    vigente_desde = DateField("Vigente desde", validators=[Optional()])
    vigente_hasta = DateField(
        "Vigente hasta",
        validators=[Optional()],
        description="Dejalo vacío si no vence.",
    )
    archivo = FileField(
        "Archivo PDF",
        validators=[Optional(), FileAllowed(["pdf"], "Solo se admiten archivos PDF.")],
    )
    status = SelectField(
        "Estado", choices=[(s, STATUS_LABELS[s]) for s in STATUSES], default="draft"
    )
    submit = SubmitField("Guardar")

    def validate(self, extra_validators=None) -> bool:  # type: ignore[override]
        if not super().validate(extra_validators):
            return False
        if self.vigente_desde.data and self.vigente_hasta.data:
            if self.vigente_hasta.data < self.vigente_desde.data:
                self.vigente_hasta.errors.append(
                    "La fecha de fin no puede ser anterior a la de inicio."
                )
                return False
        return True


class DeleteForm(FlaskForm):
    """CSRF-token-only form.

    Deletion is a POST with a token, not a bare fetch(method:'DELETE') as
    before — that had no authentication and no CSRF protection, so any website
    could delete every news item from a logged-in visitor's browser.
    """

    submit = SubmitField("Eliminar")
