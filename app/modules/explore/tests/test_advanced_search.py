from datetime import datetime, timezone

import pytest

from app import db
from app.modules.auth.models import User
from app.modules.dataset.models import Author, DataSet, DSMetaData, PublicationType
from app.modules.explore.repositories import ExploreRepository
from app.modules.featuremodel.models import FeatureModel, FMMetaData
from app.modules.profile.models import UserProfile


@pytest.fixture(scope="module")
def repo():
    return ExploreRepository()


class TestAdvancedSearch:

    @pytest.fixture(autouse=True)
    def setup_data(self):
        """
        Crea un conjunto de datos controlado antes de cada test.
        Se crea un User y se asigna 'user_id' a los Datasets.
        """
        db.create_all()

        # 1. Crear un Usuario "Dueño" para los datasets
        user = User(email="test_search@example.com", password="password")
        user.profile = UserProfile(surname="Tester", name="Search")
        db.session.add(user)
        db.session.commit()  # Confirmamos para obtener el user.id

        # --- Dataset 1 ---
        ds1 = DataSet(
            created_at=datetime(2020, 1, 1, tzinfo=timezone.utc), user_id=user.id  # <--- Asignamos el usuario
        )
        meta1 = DSMetaData(
            title="The Alpha Dataset",
            description="First generic description",
            publication_type=PublicationType.JOURNAL_ARTICLE,
            tags="tag1, common",
            dataset_doi="10.1234/dataset1",
        )
        auth1 = Author(name="Alice Smith", affiliation="University A")
        fm1 = FeatureModel()

        fm_meta1 = FMMetaData(
            uvl_filename="file1.uvl",
            title="FM Alpha",
            tags="tag1",
            description="FM Desc",
            publication_type=PublicationType.JOURNAL_ARTICLE,
        )

        fm1.fm_meta_data = fm_meta1
        meta1.authors.append(auth1)
        ds1.ds_meta_data = meta1
        ds1.feature_models.append(fm1)

        # --- Dataset 2 ---
        ds2 = DataSet(
            created_at=datetime(2023, 1, 1, tzinfo=timezone.utc), user_id=user.id  # <--- Asignamos el usuario
        )
        meta2 = DSMetaData(
            title="The Beta Collection",
            description="Second specific description about AI",
            publication_type=PublicationType.CONFERENCE_PAPER,
            tags="tag2, common",
            dataset_doi="10.1234/dataset2",
        )
        auth2 = Author(name="Bob Jones", affiliation="Company B")
        fm2 = FeatureModel()

        fm_meta2 = FMMetaData(
            uvl_filename="complex_model.uvl",
            title="FM Beta",
            tags="tag2",
            description="FM Desc",
            publication_type=PublicationType.CONFERENCE_PAPER,
        )

        fm2.fm_meta_data = fm_meta2
        meta2.authors.append(auth2)
        ds2.ds_meta_data = meta2
        ds2.feature_models.append(fm2)

        # --- Dataset 3 ---
        ds3 = DataSet(
            created_at=datetime(2021, 5, 20, tzinfo=timezone.utc), user_id=user.id  # <--- Asignamos el usuario
        )
        meta3 = DSMetaData(
            title="Gamma Ray Data",
            description="Another description",
            publication_type=PublicationType.JOURNAL_ARTICLE,
            tags="tag1",
            dataset_doi="10.1234/dataset3",
        )
        auth3 = Author(name="Alice Smith", affiliation="University A")

        meta3.authors.append(auth3)
        ds3.ds_meta_data = meta3

        # Guardar todo en DB
        db.session.add_all([ds1, ds2, ds3])
        db.session.commit()

        yield

        # Limpieza
        db.session.remove()
        db.drop_all()

    def test_filter_by_query_generic(self, repo):
        """Prueba la búsqueda general (OR logic) en título"""
        results = repo.filter(query="Alpha")
        assert len(results) == 1
        assert results[0].ds_meta_data.title == "The Alpha Dataset"

    def test_filter_by_query_author_name(self, repo):
        """Prueba que el buscador general encuentre por nombre de autor"""
        results = repo.filter(query="Bob Jones")
        assert len(results) == 1
        assert results[0].ds_meta_data.title == "The Beta Collection"

    def test_advanced_filter_author(self, repo):
        """Prueba el filtro específico de Author (AND logic)"""
        results = repo.filter(author="Alice")
        assert len(results) == 2
        titles = [r.ds_meta_data.title for r in results]
        assert "The Alpha Dataset" in titles
        assert "Gamma Ray Data" in titles

    def test_advanced_filter_date(self, repo):
        """Prueba el filtro por fecha (startswith logic)"""
        results = repo.filter(date="2020-01-01")
        assert len(results) == 1
        assert results[0].ds_meta_data.title == "The Alpha Dataset"

        results = repo.filter(date="2023")
        assert len(results) == 1
        assert results[0].ds_meta_data.title == "The Beta Collection"

    def test_advanced_filter_description(self, repo):
        """Prueba el filtro específico de descripción"""
        results = repo.filter(description="specific description")
        assert len(results) == 1
        assert results[0].ds_meta_data.title == "The Beta Collection"

    def test_advanced_filter_uvl_file(self, repo):
        """Prueba el filtro por nombre de archivo UVL"""
        results = repo.filter(uvl_files="file1")
        assert len(results) == 1
        assert results[0].ds_meta_data.title == "The Alpha Dataset"

    def test_advanced_filter_tags(self, repo):
        """Prueba el filtro por Tags"""
        results = repo.filter(tags=["tag2"])
        assert len(results) == 1
        assert results[0].ds_meta_data.title == "The Beta Collection"

        results = repo.filter(tags=["common"])
        assert len(results) == 2

    def test_combined_advanced_filters(self, repo):
        """Prueba combinando Author AND Date (Lógica AND estricta)"""
        results = repo.filter(author="Alice", date="2020")
        assert len(results) == 1
        assert results[0].ds_meta_data.title == "The Alpha Dataset"

        # Caso negativo: Alice existe, pero no en el año 2025
        results = repo.filter(author="Alice", date="2025")
        assert len(results) == 0

    def test_query_and_advanced_filters(self, repo):
        """Prueba mezclando la barra de búsqueda general Y filtros avanzados"""
        # Query general trae "common" (DS1 y DS2)
        # Filtro avanzado fuerza Author="Bob" (DS2)
        # Resultado esperado: Solo DS2
        results = repo.filter(query="common", author="Bob")
        assert len(results) == 1
        assert results[0].ds_meta_data.title == "The Beta Collection"

    def test_sorting_oldest_newest(self, repo):
        """Prueba el ordenamiento"""
        results = repo.filter(sorting="newest")
        assert results[0].ds_meta_data.title == "The Beta Collection"  # 2023

        results = repo.filter(sorting="oldest")
        assert results[0].ds_meta_data.title == "The Alpha Dataset"  # 2020
