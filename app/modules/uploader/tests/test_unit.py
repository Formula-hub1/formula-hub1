import pytest
from unittest.mock import patch, MagicMock
from app import create_app
from app.modules.dataset.models import PublicationType
import io
import base64


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test_key_uploader"
    yield app


@pytest.fixture
def client(app):
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['_user_id'] = '99'
        yield client


MOCK_PREVIEW_DATA = {
    "title": "Test Preview",
    "description": "d",
    "publication_type": PublicationType.OTHER,
    "tags": "a,b",
    "files": [{"uvl_filename": "a.uvl",
               "content_b64": base64.b64encode(b"dummy").decode('utf-8')}]
}


@pytest.fixture
def mock_uploader_service():
    """Mock para la capa de servicios del Uploader."""
    with patch('app.modules.uploader.routes.UploaderService') as MockService:
        with patch('app.modules.uploader.routes.current_user') as MockUser:
            MockUser.id = 99
            MockService.return_value.prepare_preview.return_value = \
                MOCK_PREVIEW_DATA
            MockService.return_value.save_confirmed_upload.return_value = \
                MagicMock()
            yield MockService.return_value


@patch('os.makedirs')
@patch('builtins.open')
def setup_preview_success(mock_open, mock_makedirs, client,
                          mock_uploader_service):
    """Simula una subida exitosa para establecer
       los datos de preview en la sesión."""
    data = {'file': (io.BytesIO(b'dummy'), 'test.zip')}
    client.post('/uploader/preview', data=data)


def test_index_route(client):
    """Verifica que la ruta base /uploader carga la plantilla."""
    response = client.get("/uploader")
    assert response.status_code == 200


def test_preview_upload_success(client, mock_uploader_service):
    """Verifica el flujo exitoso de previsualización con archivo."""
    data = {'file': (io.BytesIO(b'dummy'), 'test.zip')}

    with patch('os.makedirs'), patch('builtins.open'):
        response = client.post('/uploader/preview', data=data)

    assert response.status_code == 200
    mock_uploader_service.prepare_preview.assert_called_once()


def test_preview_upload_missing_input_redirects(client, mock_uploader_service):
    """Verifica la redirección si falta archivo o URL."""
    response = client.post('/uploader/preview', data={}, follow_redirects=True)

    assert response.status_code == 200
    mock_uploader_service.prepare_preview.assert_not_called()


def test_confirm_upload_success(client, mock_uploader_service):
    """Verifica el flujo completo de confirmación exitoso."""

    with patch('os.makedirs'), patch('builtins.open'):
        setup_preview_success(client, mock_uploader_service)

    data = {
        'dataset_description': 'Descripción válida de más de tres caracteres',
        'dataset_title': 'Nuevo Título',
        'dataset_publication_type': PublicationType.PAPER.value,
        'dataset_tags': 'new_tag',
        'title_0': 'File Title',
        'description_0': 'File Description'
    }

    response = client.post('/uploader/confirm', data=data)

    assert response.status_code == 200
    mock_uploader_service.save_confirmed_upload.assert_called_once()

    with client.session_transaction() as sess:
        assert "preview_data" not in sess


def test_confirm_upload_missing_session_redirects(client,
                                                  mock_uploader_service):
    """Verifica la redirección si los datos de sesión faltan."""

    with client.session_transaction() as sess:
        if "preview_data" in sess:
            del sess["preview_data"]

    response = client.post('/uploader/confirm', data={}, follow_redirects=True)

    assert response.status_code == 200
    assert b"Preview data missing" in response.data


def test_confirm_upload_short_description_redirects(client,
                                                    mock_uploader_service):
    """Verifica la redirección si la descripción es muy corta."""

    with patch('os.makedirs'), patch('builtins.open'):
        setup_preview_success(client, mock_uploader_service)

    response = client.post('/uploader/confirm',
                           data={'dataset_description': 'ab'},
                           follow_redirects=True)

    assert response.status_code == 200
    assert b"La descripcion debe tener al menos 3 caracteres" in response.data
