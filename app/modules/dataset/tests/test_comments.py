from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app import db
from app.modules.auth.models import User
from app.modules.dataset.models import Comment, DataSet, DSMetaData, PublicationType
from app.modules.profile.models import UserProfile

# ===================================================================
#  1. TESTS DEL MODELO (INTEGRACIÓN CON DB)
# ===================================================================


class TestCommentModel:
    @pytest.fixture(autouse=True)
    def setup_data(self, test_app):
        """Crea base de datos real para probar el modelo."""
        with test_app.app_context():
            db.create_all()
            user = User(email="model_test@example.com", password="password")
            user.profile = UserProfile(surname="Model", name="Tester")
            db.session.add(user)
            db.session.commit()

            self.user_id = user.id

            ds = DataSet(user_id=user.id, created_at=datetime.now(timezone.utc))
            meta = DSMetaData(
                title="Model Test Dataset",
                description="Desc",
                publication_type=PublicationType.JOURNAL_ARTICLE,
                dataset_doi="10.1234/model-test",
            )
            ds.ds_meta_data = meta
            db.session.add(ds)
            db.session.commit()

            self.dataset_id = ds.id
            yield
            db.session.remove()
            db.drop_all()

    def test_create_comment_relationship(self, test_app):
        with test_app.app_context():
            comment = Comment(content="Unit test", user_id=self.user_id, dataset_id=self.dataset_id)
            db.session.add(comment)
            db.session.commit()

            saved = Comment.query.get(comment.id)
            assert saved is not None
            assert saved.dataset_id == self.dataset_id

    def test_parent_child_relationship(self, test_app):
        with test_app.app_context():
            parent = Comment(content="P", user_id=self.user_id, dataset_id=self.dataset_id)
            db.session.add(parent)
            db.session.commit()
            child = Comment(content="C", user_id=self.user_id, dataset_id=self.dataset_id, parent_id=parent.id)
            db.session.add(child)
            db.session.commit()

            assert child in parent.children
            assert child.parent == parent

    def test_cascade_delete_orphan(self, test_app):
        with test_app.app_context():
            parent = Comment(content="P", user_id=self.user_id, dataset_id=self.dataset_id)
            db.session.add(parent)
            db.session.commit()
            child = Comment(content="C", user_id=self.user_id, dataset_id=self.dataset_id, parent_id=parent.id)
            db.session.add(child)
            db.session.commit()

            child_id = child.id
            db.session.delete(parent)
            db.session.commit()

            assert Comment.query.get(child_id) is None

    def test_to_dict(self, test_app):
        with test_app.app_context():
            parent = Comment(content="Root", user_id=self.user_id, dataset_id=self.dataset_id)
            db.session.add(parent)
            db.session.commit()
            child = Comment(content="Reply", user_id=self.user_id, dataset_id=self.dataset_id, parent_id=parent.id)
            db.session.add(child)
            db.session.commit()

            data = parent.to_dict()
            assert data["children"][0]["content"] == "Reply"


# ===================================================================
#  2. TESTS DE RUTAS (UNITARIOS CON MOCKS)
# ===================================================================


class TestCommentRoutes:

    @pytest.fixture(autouse=True)
    def setup_client(self, test_client):
        self.client = test_client
        with self.client.session_transaction() as sess:
            sess["_user_id"] = "1"  # ID falso
            sess["_fresh"] = True

    def _mock_user(self, mock_auth_cls):
        """Simula el servicio de autenticación."""
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.profile.name = "Test User"

        mock_instance = mock_auth_cls.return_value
        mock_instance.get_authenticated_user.return_value = mock_user
        return mock_user

    def _mock_dataset(self, mock_dataset_service):
        """Simula que el dataset existe cuando el controlador llama a get_or_404."""
        mock_ds = MagicMock()
        mock_ds.id = 100
        mock_ds.ds_meta_data.dataset_doi = "10.1234/test-doi"

        mock_dataset_service.get_or_404.return_value = mock_ds
        return mock_ds

    # --- Tests ---

    @patch("app.modules.dataset.routes.dataset_service")
    @patch("app.modules.dataset.routes.comment_service")
    @patch("app.modules.dataset.routes.AuthenticationService")
    def test_add_comment_route_success(self, mock_auth_cls, mock_comment_service, mock_dataset_service):
        """
        Prueba POST /datasets/<id>/comments con éxito.
        Verifica que se llama a comment_service.create y se redirige.
        """
        self._mock_user(mock_auth_cls)
        mock_ds = self._mock_dataset(mock_dataset_service)

        response = self.client.post(
            "/datasets/100/comments", data={"content": "Mocked Service Comment"}, follow_redirects=False
        )

        assert response.status_code == 302
        assert f"/doi/{mock_ds.ds_meta_data.dataset_doi}" in response.location

        mock_comment_service.create.assert_called_once_with(
            content="Mocked Service Comment", dataset_id=100, parent_id=None, user_id=1
        )

    def test_add_comment_route_empty_content(self):
        """Prueba validación: debe dar 400 sin llamar a servicios."""
        response = self.client.post(
            "/datasets/100/comments",
            data={"content": "   "},
        )
        assert response.status_code == 400

    @patch("app.modules.dataset.routes.dataset_service")
    @patch("app.modules.dataset.routes.comment_service")
    @patch("app.modules.dataset.routes.AuthenticationService")
    def test_add_reply_route(self, mock_auth_cls, mock_comment_service, mock_dataset_service):
        """Prueba envío de respuesta (Threaded reply)."""
        self._mock_user(mock_auth_cls)
        self._mock_dataset(mock_dataset_service)

        response = self.client.post(
            "/datasets/100/comments", data={"content": "This is a reply", "parent_id": "50"}  # ID del comentario padre
        )

        assert response.status_code == 302

        mock_comment_service.create.assert_called_once()
        call_args = mock_comment_service.create.call_args[1]
        assert call_args["content"] == "This is a reply"
        assert call_args["parent_id"] == "50"

    @patch("app.modules.dataset.routes.render_template")
    @patch("app.modules.dataset.routes.comment_service")
    @patch("app.modules.dataset.routes.AuthenticationService")
    def test_add_comment_ajax_success(self, mock_auth_cls, mock_comment_service, mock_render):
        """Prueba ruta AJAX simulada."""
        self._mock_user(mock_auth_cls)

        mock_render.return_value = "<div>Mocked HTML</div>"

        response = self.client.post("/datasets/100/comments/ajax", data={"content": "AJAX Comment"})

        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data["ok"] is True
        assert json_data["html"] == "<div>Mocked HTML</div>"

        mock_comment_service.create.assert_called_once()

    def test_add_comment_ajax_empty(self):
        """Prueba validación AJAX."""
        response = self.client.post(
            "/datasets/100/comments/ajax",
            data={"content": ""},
        )
        assert response.status_code == 400
        assert response.get_json()["ok"] is False

    @patch("app.modules.dataset.routes.render_template")
    @patch("app.modules.dataset.routes.Comment")
    def test_comments_fragment_get(self, mock_comment_model, mock_render):
        """Prueba GET Fragment simulando la query de base de datos."""

        mock_query = mock_comment_model.query.filter_by.return_value
        mock_query.all.return_value = ["MockComment1", "MockComment2"]

        mock_render.return_value = "HTML Fragment"

        response = self.client.get("/datasets/100/comments/fragment")

        assert response.status_code == 200

        args, kwargs = mock_comment_model.query.filter_by.call_args
        assert kwargs["dataset_id"] == 100
        assert kwargs["parent_id"] is None

        render_args, render_kwargs = mock_render.call_args
        assert render_kwargs["comments"] == ["MockComment1", "MockComment2"]
