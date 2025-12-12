"""
Community forms for Flask-WTF
"""

from flask_wtf import FlaskForm
from wtforms import BooleanField, HiddenField, SelectField, StringField, TextAreaField
from wtforms.validators import URL, DataRequired, Length, Optional, Regexp


class CommunityForm(FlaskForm):
    """Form for creating/editing communities"""

    name = StringField(
        "Nombre de la Comunidad",
        validators=[
            DataRequired(message="El nombre es obligatorio"),
            Length(min=3, max=255, message="El nombre debe tener entre 3 y 255 caracteres"),
        ],
        render_kw={"placeholder": "Ej: Machine Learning Research"},
    )

    slug = StringField(
        "Slug (identificador único)",
        validators=[
            DataRequired(message="El slug es obligatorio"),
            Length(min=3, max=255, message="El slug debe tener entre 3 y 255 caracteres"),
            Regexp("^[a-z0-9-]+$", message="El slug solo puede contener letras minúsculas, números y guiones"),
        ],
        render_kw={"placeholder": "Ej: machine-learning-research"},
    )

    description = TextAreaField(
        "Descripción",
        validators=[Optional()],
        render_kw={"placeholder": "Describe el propósito de esta comunidad...", "rows": 5},
    )

    logo_url = StringField(
        "URL del Logo",
        validators=[Optional(), URL(message="Debe ser una URL válida")],
        render_kw={"placeholder": "https://example.com/logo.png"},
    )

    website = StringField(
        "Sitio Web",
        validators=[Optional(), URL(message="Debe ser una URL válida")],
        render_kw={"placeholder": "https://example.com"},
    )

    is_public = BooleanField(
        "¿Comunidad pública?", default=True, description="Si está marcado, cualquier usuario puede ver esta comunidad"
    )


class MemberForm(FlaskForm):
    """Form for adding members to a community"""

    user_id = SelectField(
        "Usuario",
        coerce=int,
        validators=[DataRequired(message="Debes seleccionar un usuario")],
    )

    role = SelectField(
        "Rol",
        choices=[("member", "Miembro"), ("curator", "Curador"), ("owner", "Propietario")],
        default="member",
        validators=[DataRequired()],
    )


class SubmitDatasetForm(FlaskForm):
    """Form for submitting a dataset to a community"""

    dataset_id = SelectField(
        "Selecciona un dataset",
        coerce=int,
        validators=[DataRequired(message="Debes seleccionar un dataset")],
    )

    message = TextAreaField(
        "Mensaje (opcional)",
        validators=[Optional(), Length(max=1000)],
        render_kw={"placeholder": "Explica por qué este dataset es relevante para esta comunidad...", "rows": 4},
    )


class ReviewSubmissionForm(FlaskForm):
    """Form for reviewing dataset submissions"""

    action = HiddenField("Acción", validators=[DataRequired()])

    feedback = TextAreaField(
        "Feedback (requerido para rechazo)",
        validators=[Optional(), Length(max=1000)],
        render_kw={"placeholder": "Proporciona feedback sobre por qué se rechaza este dataset...", "rows": 4},
    )


class SearchForm(FlaskForm):
    """Form for searching communities"""

    query = StringField(
        "Buscar",
        validators=[DataRequired(), Length(min=1, max=255)],
        render_kw={"placeholder": "Buscar comunidades..."},
    )
