from datetime import datetime

from flask import request
from sqlalchemy import Enum as SQLAlchemyEnum

from app import db
from app.modules.dataset.models_base import Author, PublicationType  # noqa: F401
from app.modules.featuremodel.models import FeatureModel


class DSMetrics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number_of_models = db.Column(db.String(120))
    number_of_features = db.Column(db.String(120))

    def __repr__(self):
        return f"DSMetrics<models={self.number_of_models}, features={self.number_of_features}>"


class DSMetaData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    deposition_id = db.Column(db.Integer)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    publication_type = db.Column(SQLAlchemyEnum(PublicationType), nullable=False)
    publication_doi = db.Column(db.String(120))
    dataset_doi = db.Column(db.String(120))
    tags = db.Column(db.String(120))
    ds_metrics_id = db.Column(db.Integer, db.ForeignKey("ds_metrics.id"))
    ds_metrics = db.relationship("DSMetrics", uselist=False, backref="ds_meta_data", cascade="all, delete")
    authors = db.relationship("Author", backref="ds_meta_data", lazy=True, cascade="all, delete")


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(50), nullable=False)

    parent_id = db.Column(db.Integer, db.ForeignKey("comment.id", ondelete="CASCADE"), nullable=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey("dataset.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User")

    children = db.relationship(
        "Comment", backref=db.backref("parent", remote_side=[id]), cascade="all, delete-orphan", single_parent=True
    )

    def to_dict(self):
        return {"id": self.id, "content": self.content, "children": [child.to_dict() for child in self.children]}


class DataSet(db.Model):
    __tablename__ = "dataset"
    id = db.Column(db.Integer, primary_key=True)
    dataset_type = db.Column(db.String(50), nullable=False)  # Clave Polimórfica
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    recalculated_at = db.Column(db.DateTime, nullable=True)
    recommended_datasets_json = db.Column(db.Text, nullable=True, default="[]")

    ds_meta_data_id = db.Column(db.Integer, db.ForeignKey("ds_meta_data.id"), nullable=False)
    ds_meta_data = db.relationship("DSMetaData", backref=db.backref("dataset", uselist=False, lazy="joined"))
    feature_models = db.relationship("FeatureModel", backref="dataset", lazy=True, cascade="all, delete")

    comments = db.relationship("Comment", backref="dataset", cascade="all, delete-orphan", lazy=True)

    __mapper_args__ = {
        "polymorphic_on": dataset_type,
        "polymorphic_identity": "base",
    }

    def name(self):
        return self.ds_meta_data.title

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def get_files_count(self):
        """Método base: Por defecto 0 si no se sobrescribe."""
        return 0

    def get_file_total_size(self):
        """Método base: Por defecto 0 bytes."""
        return 0

    def get_file_total_size_for_human(self):
        """Método base que usa el servicio de tamaño."""
        from app.modules.dataset.services import SizeService

        return SizeService().get_human_readable_size(self.get_file_total_size())

    def get_cleaned_publication_type(self):
        return self.ds_meta_data.publication_type.name.replace("_", " ").title()

    def get_zenodo_url(self):
        return f"https://zenodo.org/record/{self.ds_meta_data.deposition_id}" if self.ds_meta_data.dataset_doi else None

    def get_uvlhub_doi(self):
        from app.modules.dataset.services import DataSetService

        return DataSetService().get_uvlhub_doi(self)

    def to_dict(self):
        return {
            "title": self.ds_meta_data.title,
            "id": self.id,
            "created_at": self.created_at,
            "created_at_timestamp": int(self.created_at.timestamp()),
            "description": self.ds_meta_data.description,
            "authors": [author.to_dict() for author in self.ds_meta_data.authors],
            "publication_type": self.get_cleaned_publication_type(),
            "publication_doi": self.ds_meta_data.publication_doi,
            "dataset_doi": self.ds_meta_data.dataset_doi,
            "tags": self.ds_meta_data.tags.split(",") if self.ds_meta_data.tags else [],
            "url": self.get_uvlhub_doi(),
            "download": f'{request.host_url.rstrip("/")}/dataset/download/{self.id}',
            "zenodo": self.get_zenodo_url(),
            "dataset_type": self.dataset_type,
        }

    def __repr__(self):
        return f"DataSet<{self.id}>"


# ==========================================
# CLASE HIJA: UVLDataSet (Específico)
# ==========================================
class UVLDataSet(DataSet):
    __tablename__ = "uvl_dataset"

    # Clave primaria que apunta a la base (Joined Table Inheritance)
    id = db.Column(db.Integer, db.ForeignKey("dataset.id"), primary_key=True)

    # Relación específica de UVL
    feature_models = db.relationship(
        "FeatureModel",
        # primaryjoin="FeatureModel.dataset_id == foreign(UVLDataSet.id)",
        foreign_keys=[FeatureModel.dataset_id],
        backref=db.backref("uvl_dataset", overlaps="dataset, feature_models"),
        lazy=True,
        cascade="all, delete",
        overlaps="dataset",
    )

    __mapper_args__ = {
        "polymorphic_identity": "uvl",
    }

    # Lógica y Métodos ESPECÍFICOS de UVL
    def files(self):
        return [file for fm in self.feature_models for file in fm.files]

    def get_files_count(self):
        return sum(len(fm.files) for fm in self.feature_models)

    def get_file_total_size(self):
        return sum(file.size for fm in self.feature_models for file in fm.files)

    def get_file_total_size_for_human(self):
        from app.modules.dataset.services import SizeService

        return SizeService().get_human_readable_size(self.get_file_total_size())

    def get_uvlhub_doi(self):
        from app.modules.dataset.services import DataSetService

        return DataSetService().get_uvlhub_doi(self)

    def to_dict(self):
        data = super().to_dict()
        data.update(
            {
                "files": [file.to_dict() for fm in self.feature_models for file in fm.files],
                "files_count": self.get_files_count(),
                "total_size_in_bytes": self.get_file_total_size(),
                "total_size_in_human_format": self.get_file_total_size_for_human(),
            }
        )
        return data


class RawDataSet(DataSet):
    __tablename__ = "raw_dataset"
    id = db.Column(db.Integer, db.ForeignKey("dataset.id"), primary_key=True)

    __mapper_args__ = {
        "polymorphic_identity": "raw_dataset",
    }


class FormulaDataSet(DataSet):
    __tablename__ = "formula_dataset"

    # Clave primaria enlazada con la tabla base "dataset"
    id = db.Column(db.Integer, db.ForeignKey("dataset.id"), primary_key=True)

    # Datos globales de la carrera (comunes a todas las filas del CSV)
    nombre_gp = db.Column(db.String(200), nullable=False)
    anio_temporada = db.Column(db.Integer, nullable=False)
    fecha_carrera = db.Column(db.Date, nullable=False)
    circuito = db.Column(db.String(200), nullable=False)

    # Resultados por piloto
    results = db.relationship(
        "FormulaResult",
        backref="formula_dataset",
        cascade="all, delete-orphan",
        lazy=True,
    )

    __mapper_args__ = {
        "polymorphic_identity": "formula",  # valor que irá en dataset.dataset_type
    }

    def to_dict(self):
        data = super().to_dict()
        data.update(
            {
                "nombre_gp": self.nombre_gp,
                "anio_temporada": self.anio_temporada,
                "fecha_carrera": self.fecha_carrera.isoformat() if self.fecha_carrera else None,
                "circuito": self.circuito,
                "results": [r.to_dict() for r in self.results],
            }
        )
        return data


class FormulaResult(db.Model):
    __tablename__ = "formula_result"

    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey("formula_dataset.id"), nullable=False)

    piloto_nombre = db.Column(db.String(120), nullable=False)
    equipo = db.Column(db.String(120), nullable=False)
    motor = db.Column(db.String(120), nullable=True)

    # String porque puede ser "1", "DNF", "15", etc.
    posicion_final = db.Column(db.String(20), nullable=False)

    puntos_obtenidos = db.Column(db.Float, nullable=False, default=0.0)
    tiempo_carrera = db.Column(db.String(50), nullable=True)
    vueltas_completadas = db.Column(db.Integer, nullable=True)
    estado_carrera = db.Column(db.String(120), nullable=True)

    def to_dict(self):
        return {
            "piloto_nombre": self.piloto_nombre,
            "equipo": self.equipo,
            "motor": self.motor,
            "posicion_final": self.posicion_final,
            "puntos_obtenidos": self.puntos_obtenidos,
            "tiempo_carrera": self.tiempo_carrera,
            "vueltas_completadas": self.vueltas_completadas,
            "estado_carrera": self.estado_carrera,
        }


class DSDownloadRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey("dataset.id"))
    download_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    download_cookie = db.Column(db.String(36), nullable=False)  # Assuming UUID4 strings

    def __repr__(self):
        return (
            f"<Download id={self.id} "
            f"dataset_id={self.dataset_id} "
            f"date={self.download_date} "
            f"cookie={self.download_cookie}>"
        )


class DSViewRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey("dataset.id"))
    view_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    view_cookie = db.Column(db.String(36), nullable=False)  # Assuming UUID4 strings

    def __repr__(self):
        return f"<View id={self.id} dataset_id={self.dataset_id} date={self.view_date} cookie={self.view_cookie}>"


class DOIMapping(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dataset_doi_old = db.Column(db.String(120))
    dataset_doi_new = db.Column(db.String(120))
