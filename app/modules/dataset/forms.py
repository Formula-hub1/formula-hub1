from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import FieldList, FormField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import URL, DataRequired, Optional

from app.modules.dataset.models_base import PublicationType


class AuthorForm(FlaskForm):
    """Formulario para capturar los datos de un autor."""

    name = StringField("Name", validators=[DataRequired()])
    affiliation = StringField("Affiliation")
    orcid = StringField("ORCID")
    gnd = StringField("GND")

    class Meta:
        csrf = False  # deshabilitar CSRF porque es un subformulario

    def get_author(self):
        return {
            "name": self.name.data,
            "affiliation": self.affiliation.data,
            "orcid": self.orcid.data,
        }


class FeatureModelForm(FlaskForm):
    """Formulario para los metadatos de un modelo de características UVL."""

    uvl_filename = StringField("UVL Filename", validators=[DataRequired()])
    title = StringField("Title", validators=[Optional()])
    desc = TextAreaField("Description", validators=[Optional()])
    publication_type = SelectField(
        "Publication type",
        choices=[(pt.value, pt.name.replace("_", " ").title()) for pt in PublicationType],
        validators=[Optional()],
    )
    publication_doi = StringField("Publication DOI", validators=[Optional(), URL()])
    tags = StringField("Tags (separated by commas)")
    version = StringField("UVL Version")
    authors = FieldList(FormField(AuthorForm))

    class Meta:
        csrf = False  # deshabilitar CSRF porque es un subformulario

    def get_authors(self):
        return [author.get_author() for author in self.authors]

    def get_fmmetadata(self):
        return {
            "uvl_filename": self.uvl_filename.data,
            "title": self.title.data,
            "description": self.desc.data,
            "publication_type": self.publication_type.data,
            "publication_doi": self.publication_doi.data,
            "tags": self.tags.data,
            "uvl_version": self.version.data,
        }


class BaseDatasetForm(FlaskForm):
    """Clase base que contiene los campos de metadatos comunes a todos los tipos de Datasets."""

    title = StringField("Title", validators=[DataRequired()])
    desc = TextAreaField("Description", validators=[DataRequired()])
    publication_type = SelectField(
        "Publication type",
        choices=[(pt.value, pt.name.replace("_", " ").title()) for pt in PublicationType],
        validators=[DataRequired()],
    )
    publication_doi = StringField("Publication DOI", validators=[Optional(), URL()])
    dataset_doi = StringField("Dataset DOI", validators=[Optional(), URL()])
    tags = StringField("Tags (separated by commas)")
    authors = FieldList(FormField(AuthorForm))

    def convert_publication_type(self, value):
        """Convierte el valor del formulario a la cadena de nombre de enumeración."""
        for pt in PublicationType:
            if pt.value == value:
                return pt.name
        return "NONE"

    def get_dsmetadata(self):
        """Recopila los metadatos comunes para el modelo DSMetaData."""
        publication_type_converted = self.convert_publication_type(self.publication_type.data)

        return {
            "title": self.title.data,
            "description": self.desc.data,
            "publication_type": publication_type_converted,
            "publication_doi": self.publication_doi.data,
            "dataset_doi": self.dataset_doi.data,
            "tags": self.tags.data,
        }

    def get_authors(self):
        """Recopila los datos de la lista de autores."""
        return [author.get_author() for author in self.authors]


class FormulaDataSetForm(BaseDatasetForm):
    """Formulario específico para Datasets de Fórmula 1 (CSV)."""

    # Campo para subir el archivo CSV
    # FileRequired: Obliga a subir un archivo
    # FileAllowed: Solo permite extensiones .csv
    csv_file = FileField("Upload CSV File", validators=[FileRequired(), FileAllowed(["csv"], "CSV files only!")])

    submit = SubmitField("Submit Formula 1 Dataset")


class UVLDataSetForm(BaseDatasetForm):  # HEREDA los campos comunes de la clase base
    """Formulario específico para la carga de Datasets UVL."""

    # Campo específico de UVL
    feature_models = FieldList(FormField(FeatureModelForm), min_entries=1)

    submit = SubmitField("Submit UVL Dataset")

    # El método get_dsmetadata y get_authors son HEREDADOS.

    def get_feature_models(self):
        """Recopila los metadatos de los modelos de características."""
        # Se requiere este método aquí para obtener los datos específicos de UVL
        return [fm.get_fmmetadata() for fm in self.feature_models]


class RawDataSetForm(BaseDatasetForm):  # HEREDA los campos comunes de la clase base
    """Formulario específico para la carga de Datasets genéricos (raw)."""

    submit = SubmitField("Create Generic Dataset")
