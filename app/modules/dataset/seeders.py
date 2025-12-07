import os
import shutil
from datetime import date, datetime, timezone

from dotenv import load_dotenv

from app.modules.auth.models import User

# IMPORTAMOS LOS NUEVOS MODELOS
from app.modules.dataset.models import (
    Author,
    DSMetaData,
    DSMetrics,
    FormulaDataSet,
    FormulaResult,
    PublicationType,
    UVLDataSet,
)
from app.modules.featuremodel.models import FeatureModel, FMMetaData
from app.modules.hubfile.models import Hubfile
from core.seeders.BaseSeeder import BaseSeeder


class DataSetSeeder(BaseSeeder):

    priority = 2  # Lower priority

    def run(self):
        # Retrieve users
        user1 = User.query.filter_by(email="user1@example.com").first()
        user2 = User.query.filter_by(email="user2@example.com").first()

        if not user1 or not user2:
            raise Exception("Users not found. Please seed users first.")

        # Create DSMetrics instance
        ds_metrics = DSMetrics(number_of_models="5", number_of_features="50")
        seeded_ds_metrics = self.seed([ds_metrics])[0]

        # ---------------------------------------------------------
        # PARTE 1: DATASETS UVL
        # ---------------------------------------------------------
        ds_meta_data_list = [
            DSMetaData(
                deposition_id=1 + i,
                title=f"Sample dataset {i + 1}",
                description=f"Description for dataset {i + 1}",
                publication_type=PublicationType.DATA_MANAGEMENT_PLAN,
                publication_doi=f"10.1234/dataset{i + 1}",
                dataset_doi=f"10.1234/dataset{i + 1}",
                tags="tag1, tag2",
                ds_metrics_id=seeded_ds_metrics.id,
            )
            for i in range(4)
        ]
        seeded_ds_meta_data = self.seed(ds_meta_data_list)

        authors = [
            Author(
                name=f"Author {i + 1}",
                affiliation=f"Affiliation {i + 1}",
                orcid=f"0000-0000-0000-000{i}",
                ds_meta_data_id=seeded_ds_meta_data[i % 4].id,
            )
            for i in range(4)
        ]
        self.seed(authors)

        datasets = [
            UVLDataSet(
                user_id=user1.id if i % 2 == 0 else user2.id,
                ds_meta_data_id=seeded_ds_meta_data[i].id,
                created_at=datetime.now(timezone.utc),
            )
            for i in range(4)
        ]
        seeded_datasets = self.seed(datasets)

        fm_meta_data_list = [
            FMMetaData(
                uvl_filename=f"file{i + 1}.uvl",
                title=f"Feature Model {i + 1}",
                description=f"Description for feature model {i + 1}",
                publication_type=PublicationType.SOFTWARE_DOCUMENTATION,
                publication_doi=f"10.1234/fm{i + 1}",
                tags="tag1, tag2",
                uvl_version="1.0",
            )
            for i in range(12)
        ]
        seeded_fm_meta_data = self.seed(fm_meta_data_list)

        fm_authors = [
            Author(
                name=f"Author {i + 5}",
                affiliation=f"Affiliation {i + 5}",
                orcid=f"0000-0000-0000-000{i + 5}",
                fm_meta_data_id=seeded_fm_meta_data[i].id,
            )
            for i in range(12)
        ]
        self.seed(fm_authors)

        feature_models = [
            FeatureModel(dataset_id=seeded_datasets[i // 3].id, fm_meta_data_id=seeded_fm_meta_data[i].id)
            for i in range(12)
        ]
        seeded_feature_models = self.seed(feature_models)

        load_dotenv()
        working_dir = os.getenv("WORKING_DIR", "")
        src_folder = os.path.join(working_dir, "app", "modules", "dataset", "uvl_examples")
        for i in range(12):
            file_name = f"file{i + 1}.uvl"
            feature_model = seeded_feature_models[i]
            dataset = next(ds for ds in seeded_datasets if ds.id == feature_model.dataset_id)
            user_id = dataset.user_id

            dest_folder = os.path.join(working_dir, "uploads", f"user_{user_id}", f"dataset_{dataset.id}")
            os.makedirs(dest_folder, exist_ok=True)
            shutil.copy(os.path.join(src_folder, file_name), dest_folder)

            file_path = os.path.join(dest_folder, file_name)

            uvl_file = Hubfile(
                name=file_name,
                checksum=f"checksum{i + 1}",
                size=os.path.getsize(file_path),
                feature_model_id=feature_model.id,
            )
            self.seed([uvl_file])

        # ---------------------------------------------------------
        # PARTE 2: NUEVO DATASET DE FÓRMULA 1
        # ---------------------------------------------------------

        # 1. Crear Metadatos
        f1_meta = DSMetaData(
            deposition_id=999,
            title="Gran Premio de España 2024",
            description="Resultados oficiales de la carrera de F1 en Barcelona.",
            publication_type=PublicationType.OTHER,
            publication_doi="10.1234/f1-spain-2024",
            dataset_doi="10.1234/f1-spain-2024",
            tags="f1, formula 1, racing, 2024",
            ds_metrics_id=seeded_ds_metrics.id,
        )
        seeded_f1_meta = self.seed([f1_meta])[0]

        # 2. Crear Dataset
        f1_dataset = FormulaDataSet(
            user_id=user1.id,
            ds_meta_data_id=seeded_f1_meta.id,
            created_at=datetime.now(timezone.utc),
            nombre_gp="Gran Premio de España",
            anio_temporada=2024,
            fecha_carrera=date(2024, 6, 23),
            circuito="Circuit de Barcelona-Catalunya",
        )
        seeded_f1_dataset = self.seed([f1_dataset])[0]

        # 3. Crear Resultados
        f1_results = [
            FormulaResult(
                dataset_id=seeded_f1_dataset.id,
                piloto_nombre="Max Verstappen",
                equipo="Red Bull Racing",
                motor="Honda RBPT",
                posicion_final="1",
                puntos_obtenidos=25.0,
                tiempo_carrera="1:35:48.333",
                vueltas_completadas=66,
                estado_carrera="Terminado",
            ),
            FormulaResult(
                dataset_id=seeded_f1_dataset.id,
                piloto_nombre="Lando Norris",
                equipo="McLaren",
                motor="Mercedes",
                posicion_final="2",
                puntos_obtenidos=18.0,
                tiempo_carrera="1:35:48.653",
                vueltas_completadas=66,
                estado_carrera="Terminado",
            ),
        ]
        self.seed(f1_results)
