"""Contact form.

The original form was ``method=GET`` pointing at a static HTML file, so every
submission put the sender's name, email, phone and message into the URL — and
then reached no server at all. Validation was client-side only and therefore
advisory.
"""

from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional, Regexp

from itsc.models.contact import MOTIVOS


class ContactForm(FlaskForm):
    asunto = StringField(
        "Asunto",
        validators=[DataRequired("Indicá el asunto."), Length(min=3, max=200)],
    )
    nombre = StringField(
        "Nombre y apellido",
        validators=[DataRequired("Ingresá tu nombre."), Length(min=2, max=120)],
    )
    email = StringField(
        "Email",
        validators=[
            DataRequired("Ingresá tu email."),
            Email("Ingresá un email válido."),
            Length(max=254),
        ],
    )
    telefono = StringField(
        "Teléfono",
        validators=[
            Optional(),
            Regexp(r"^\+?[\d\s()-]{6,30}$", message="Ingresá un teléfono válido."),
        ],
        description="Opcional.",
    )
    motivo = SelectField(
        "Motivo de contacto",
        choices=[(m, m) for m in MOTIVOS],
        validators=[DataRequired("Elegí un motivo.")],
    )
    mensaje = TextAreaField(
        "Mensaje",
        validators=[
            DataRequired("Escribí tu consulta."),
            Length(min=15, max=5000, message="El mensaje debe tener al menos 15 caracteres."),
        ],
    )
    #: Honeypot. Hidden from humans; bots that fill every field trip it.
    website = StringField("No completar", validators=[Optional()])
    submit = SubmitField("Enviar consulta")

    def is_bot(self) -> bool:
        return bool(self.website.data)
