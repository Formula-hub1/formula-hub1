import pytest

from app import create_app
from app.modules.fakenodo.models import Fakenodo
from app.modules.fakenodo.repositories import FakenodoRepository
from app.modules.fakenodo.routes import FAKE_ZENODO_RECORDS
from app.modules.fakenodo.services import FakenodoService


@pytest.fixture
def app():
    # Configuración de la aplicación
    app = create_app()
    app.config["TESTING"] = True

    # Limpiar el estado global (FAKE_ZENODO_RECORDS) antes y después de cada test
    # Es crucial para la lógica de versiones/DOI
    FAKE_ZENODO_RECORDS.clear()
    yield app
    FAKE_ZENODO_RECORDS.clear()


@pytest.fixture
def client(app):
    return app.test_client()


# --- Función Auxiliar ---


def _create_deposition(client, metadata=None):
    """Crea un depósito y retorna su ID."""
    response = client.post("/fakenodo/api", json=metadata)
    assert response.status_code == 201
    return response.get_json()["id"]


# --- TESTS BÁSICOS DE ENDPOINTS ---


def test_01_fakenodo_api_is_running(client):
    # Test GET /fakenodo/api (Health Check)
    response = client.get("/fakenodo/api")
    assert response.status_code == 200
    assert response.get_json()["status"] == "success"


def test_02_create_deposition_success(client):
    # Test POST /fakenodo/api
    dep_id = _create_deposition(client)
    assert dep_id in FAKE_ZENODO_RECORDS


def test_03_create_with_metadata_sets_updated_flag(client):
    # Test que la metadata_updated se pone a True al crear con JSON
    _create_deposition(client, metadata={"title": "Test"})

    # Recuperamos el ID del último registro creado
    dep_id = list(FAKE_ZENODO_RECORDS.keys())[0]
    assert FAKE_ZENODO_RECORDS[dep_id]["metadata_updated"]


# --- TESTS DE GESTIÓN DE ARCHIVOS ---


def test_04_add_file_sets_files_updated_flag(client):
    # Crear y subir archivo
    dep_id = _create_deposition(client)
    response = client.post(f"/fakenodo/api/{dep_id}/files", data=b"file content")

    assert response.status_code == 201
    # Verificar que el flag files_updated se activa en el mock
    assert FAKE_ZENODO_RECORDS[dep_id]["files_updated"]


# --- TESTS DE LÓGICA DE VERSIÓN Y DOI ---


def test_05_publish_initial_version_v1(client):
    # Crear y publicar V1
    dep_id = _create_deposition(client)

    response = client.post(f"/fakenodo/api/{dep_id}/actions/publish")
    data = response.get_json()

    assert response.status_code == 202
    assert data["version"] == 1
    assert "v1" in data["doi"]


def test_06_publish_metadata_only_retains_version(client):
    # Crear y publicar V1
    dep_id = _create_deposition(client)
    client.post(f"/fakenodo/api/{dep_id}/actions/publish")
    doi_v1 = FAKE_ZENODO_RECORDS[dep_id]["doi"]

    # Simular solo cambio de metadata (activar flag)
    FAKE_ZENODO_RECORDS[dep_id]["metadata_updated"] = True

    # Republish (debe mantener V1)
    response = client.post(f"/fakenodo/api/{dep_id}/actions/publish")
    data = response.get_json()

    assert data["version"] == 1
    assert data["doi"] == doi_v1


def test_07_publish_after_file_change_creates_v2(client):
    # Crear y publicar V1
    dep_id = _create_deposition(client)
    client.post(f"/fakenodo/api/{dep_id}/actions/publish")
    doi_v1 = FAKE_ZENODO_RECORDS[dep_id]["doi"]

    # Cambiar archivos (activa files_updated=True)
    client.post(f"/fakenodo/api/{dep_id}/files", data=b"new content")

    # Publicar V2
    response = client.post(f"/fakenodo/api/{dep_id}/actions/publish")
    data = response.get_json()

    assert response.status_code == 202
    assert data["version"] == 2
    assert "v2" in data["doi"]
    assert data["doi"] != doi_v1


# --- TESTS DE ELIMINACIÓN Y ERRORES ---


def test_08_delete_deposition_success(client):
    dep_id = _create_deposition(client)

    # Eliminar
    response = client.delete(f"/fakenodo/api/{dep_id}")
    assert response.status_code == 200

    # Verificar eliminación
    assert dep_id not in FAKE_ZENODO_RECORDS


def test_09_404_not_found_errors(client):
    non_existent_id = "non_existent_id"

    # Probar 404 para las cuatro rutas que manejan IDs
    assert client.get(f"/fakenodo/api/{non_existent_id}").status_code == 404
    assert client.delete(f"/fakenodo/api/{non_existent_id}").status_code == 404
    assert client.post(f"/fakenodo/api/{non_existent_id}/files").status_code == 404
    assert client.post(f"/fakenodo/api/{non_existent_id}/actions/publish").status_code == 404


# --- TESTS DE COMPONENTES INTERNOS (MODEL, REPO, SERVICE) ---


def test_10_fakenodo_model_instantiation_and_repr():
    # Verifica la instanciación del modelo
    fakenodo_instance = Fakenodo(id=99)
    assert fakenodo_instance.id == 99
    assert repr(fakenodo_instance) == "Fakenodo<99>"


def test_11_fakenodo_repository_instantiation():
    # Verifica que el repositorio se inicialice correctamente
    repo = FakenodoRepository()
    assert repo is not None


def test_12_fakenodo_service_instantiation():
    # Verifica que el servicio se inicialice correctamente
    service = FakenodoService()
    assert service is not None
