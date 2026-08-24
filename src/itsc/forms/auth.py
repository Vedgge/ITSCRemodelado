"""Authentication forms."""

from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Length


class LoginForm(FlaskForm):
    username = StringField(
        "Usuario",
        validators=[DataRequired("Ingresá tu usuario."), Length(max=64)],
    )
    password = PasswordField(
        "Contraseña",
        validators=[DataRequired("Ingresá tu contraseña."), Length(max=256)],
    )
    remember = BooleanField("Mantener la sesión iniciada")
    submit = SubmitField("Ingresar")
