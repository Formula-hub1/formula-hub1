import io
import base64
import zipfile
import pytest
from unittest.mock import Mock, patch
from flask import Flask
from app.modules.uploader.services import (
    UploaderService,
    calculate_checksum_and_size_bytes
)
from app.modules.uploader.repositories import UploaderRepository
from app.modules.uploader.forms import UploaderForm
from app.modules.uploader.models import Uploader
from app.modules.dataset.models import PublicationType


class TestCalculateChecksumAndSize:
    """Tests para la función de utilidad de checksum."""

    def test_calculate_checksum_basic(self):
        content = b"test content"
        checksum, size = calculate_checksum_and_size_bytes(content)

        assert isinstance(checksum, str)
        assert len(checksum) == 64  # SHA256 hex
        assert size == len(content)

    def test_calculate_checksum_empty(self):
        content = b""
        checksum, size = calculate_checksum_and_size_bytes(content)

        assert isinstance(checksum, str)
        assert size == 0


class TestUploaderService:
    """Tests para UploaderService."""

    @pytest.fixture
    def service(self, tmp_path):
        """Fixture que crea un servicio con directorio temporal."""
        with patch('app.modules.uploader.services.Path') as mock_path:
            mock_path_instance = mock_path.return_value.resolve.return_value
            mock_path_instance.parent.parent.parent.parent = tmp_path
            service = UploaderService()
            service.base_upload_dir = tmp_path / "uploads"
            service.base_upload_dir.mkdir(exist_ok=True)
            return service

    @pytest.fixture
    def sample_zip(self):
        """Fixture que crea un ZIP con archivos .uvl de ejemplo."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr("model1.uvl", "features\n  Feature1")
            zf.writestr("subdir/model2.uvl", "features\n  Feature2")
        return zip_buffer.getvalue()

    def test_prepare_zip_preview_success(self, service, sample_zip):
        """Test preparación de preview desde ZIP válido."""
        result = service._prepare_zip_preview(sample_zip, "test.zip")

        assert result["title"] == "test.zip"
        assert result["publication_type"] == PublicationType.OTHER
        assert len(result["files"]) == 2
        assert result["files"][0]["uvl_filename"] == "model1.uvl"
        assert "content_b64" in result["files"][0]
        assert result["files"][0]["title"] == "model1.uvl"

    def test_prepare_zip_preview_no_uvl_files(self, service):
        """Test con ZIP sin archivos .uvl."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr("readme.txt", "some text")

        with pytest.raises(ValueError, match="No se encontraron archivos"):
            service._prepare_zip_preview(zip_buffer.getvalue(), "empty.zip")

    def test_prepare_preview_with_file(self, service, sample_zip):
        """Test prepare_preview con archivo."""
        mock_file = Mock()
        mock_file.filename = "test.zip"
        mock_file.read.return_value = sample_zip

        result = service.prepare_preview(mock_file, None)

        assert result["title"] == "test.zip"
        assert len(result["files"]) == 2

    @patch('app.modules.uploader.services.requests.get')
    def test_prepare_preview_with_github_url(
        self, mock_get, service, sample_zip
    ):
        """Test prepare_preview con URL de GitHub."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = sample_zip
        mock_get.return_value = mock_response

        url = "https://github.com/user/repo/archive.zip"
        result = service.prepare_preview(None, url)

        assert result["title"] == url
        assert len(result["files"]) == 2
        mock_get.assert_called_once()

    @patch('app.modules.uploader.services.requests.get')
    def test_prepare_preview_github_url_fails(self, mock_get, service):
        """Test con URL de GitHub que falla."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        url = "https://github.com/user/repo/archive.zip"
        with pytest.raises(ValueError, match="GitHub URL no descargable"):
            service.prepare_preview(None, url)

    def test_prepare_preview_no_input(self, service):
        """Test sin archivo ni URL."""
        with pytest.raises(ValueError, match="No ZIP o GitHub URL"):
            service.prepare_preview(None, None)

    @patch('builtins.open', create=True)
    @patch('app.modules.uploader.services.Hubfile')
    @patch('app.modules.uploader.services.FeatureModel')
    @patch('app.modules.uploader.services.FMMetaData')
    @patch('app.modules.uploader.services.DataSet')
    @patch('app.modules.uploader.services.DSMetaData')
    @patch('app.modules.uploader.services.shutil.rmtree')
    @patch('app.modules.uploader.services.os.path.exists')
    @patch('app.modules.uploader.services.os.makedirs')
    @patch('app.modules.uploader.services.db.session')
    def test_save_confirmed_upload(
        self, mock_session, mock_makedirs, mock_exists, mock_rmtree,
        mock_ds_meta_class, mock_dataset_class, mock_fm_meta_class,
        mock_fm_class, mock_hubfile_class, mock_open, service, tmp_path
    ):
        """Test guardado de upload confirmado."""
        # Setup
        service.base_upload_dir = tmp_path
        temp_folder_path = str(tmp_path / "temp")

        # Mock de modelos
        mock_ds_meta = Mock()
        mock_ds_meta.id = 1
        mock_ds_meta_class.return_value = mock_ds_meta

        mock_dataset = Mock()
        mock_dataset.id = 1
        mock_dataset_class.return_value = mock_dataset

        mock_fm_meta = Mock()
        mock_fm_meta.id = 1
        mock_fm_meta_class.return_value = mock_fm_meta

        mock_fm = Mock()
        mock_fm.id = 1
        mock_fm_class.return_value = mock_fm

        mock_exists.return_value = True

        # Mock current_user con PropertyMock para temp_folder
        with patch('app.modules.uploader.services.current_user') as mock_user:
            mock_user.temp_folder = Mock(return_value=temp_folder_path)

            content_b64 = base64.b64encode(b"test content").decode("utf-8")
            data = {
                "title": "Test Dataset",
                "description": "Test description",
                "publication_type": PublicationType.OTHER,
                "tags": "test,tags",
                "files": [{
                    "uvl_filename": "test.uvl",
                    "content_b64": content_b64,
                    "title": "Test File",
                    "description": "Test file description"
                }]
            }

            result = service.save_confirmed_upload(data, user_id=1)

            assert result == mock_dataset
            assert mock_session.add.called
            assert mock_session.commit.called


class TestUploaderRepository:
    """Tests para UploaderRepository."""

    def test_repository_initialization(self):
        """Test inicialización del repositorio."""
        repo = UploaderRepository()
        assert repo.model is not None


class TestUploaderForm:
    """Tests para UploaderForm."""

    def test_form_has_required_fields(self):
        """Test que el formulario tiene los campos requeridos."""
        app = Flask(__name__)
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SECRET_KEY'] = 'test-secret-key'

        with app.app_context():
            form = UploaderForm()
            assert hasattr(form, 'file')
            assert hasattr(form, 'url')
            assert hasattr(form, 'submit')


class TestUploaderModel:
    """Tests para el modelo Uploader."""

    def test_uploader_repr(self):
        """Test representación string del modelo."""
        uploader = Uploader()
        uploader.id = 123

        assert repr(uploader) == 'Uploader<123>'
