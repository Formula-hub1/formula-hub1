from unittest.mock import MagicMock, patch

import pytest

from app import db
from app.modules.auth.models import User
from app.modules.community.services import NotificationService
from app.modules.profile.models import UserProfile


@pytest.fixture(scope="module")
def test_client(test_client):
    """Extends the test_client fixture for module testing."""
    with test_client.application.app_context():
        user = User.query.filter_by(email="test@example.com").first()
        if user and not user.profile:
            profile = UserProfile(user_id=user.id, name="Test", surname="User")
            db.session.add(profile)
            db.session.commit()

    yield test_client


class TestNotificationService:

    def _create_mock_submission(self):
        """Create a mock submission with all required attributes"""
        mock_submission = MagicMock()
        mock_submission.id = 1
        mock_submission.message = "Test message"
        mock_submission.feedback = "Test feedback"

        mock_community = MagicMock()
        mock_community.id = 1
        mock_community.name = "Test Community"
        mock_community.slug = "test-community"

        mock_curator = MagicMock()
        mock_curator.email = "curator@example.com"
        mock_community.get_curators.return_value = [mock_curator]
        mock_community.get_owners.return_value = []

        mock_dataset = MagicMock()
        mock_dataset.ds_meta_data.title = "Test Dataset"
        mock_dataset.ds_meta_data.dataset_doi = "10.1234/test"

        mock_submitter = MagicMock()
        mock_submitter.email = "submitter@example.com"
        mock_submitter.profile.name = "Submitter Name"

        mock_reviewer = MagicMock()
        mock_reviewer.email = "reviewer@example.com"
        mock_reviewer.profile.name = "Reviewer Name"

        mock_submission.community = mock_community
        mock_submission.dataset = mock_dataset
        mock_submission.submitter = mock_submitter
        mock_submission.reviewer = mock_reviewer

        return mock_submission

    @patch("app.modules.community.services.url_for")
    @patch("app.modules.community.services.mail_manager")
    def test_send_new_submission_notification_calls_send_email(self, mock_mail, mock_url_for, test_client):
        """Test that new submission notification calls send_email"""
        with test_client.application.app_context():
            mock_url_for.return_value = "http://localhost/test"
            mock_submission = self._create_mock_submission()

            NotificationService.send_new_submission_notification(mock_submission)

            mock_mail.send_email.assert_called_once()

    @patch("app.modules.community.services.url_for")
    @patch("app.modules.community.services.mail_manager")
    def test_send_new_submission_notification_correct_recipient(self, mock_mail, mock_url_for, test_client):
        """Test that new submission notification is sent to curator"""
        with test_client.application.app_context():
            mock_url_for.return_value = "http://localhost/test"
            mock_submission = self._create_mock_submission()

            NotificationService.send_new_submission_notification(mock_submission)

            call_args = mock_mail.send_email.call_args
            assert call_args.kwargs["to"] == "curator@example.com"

    @patch("app.modules.community.services.url_for")
    @patch("app.modules.community.services.mail_manager")
    def test_send_new_submission_notification_correct_subject(self, mock_mail, mock_url_for, test_client):
        """Test that new submission notification has correct subject"""
        with test_client.application.app_context():
            mock_url_for.return_value = "http://localhost/test"
            mock_submission = self._create_mock_submission()

            NotificationService.send_new_submission_notification(mock_submission)

            call_args = mock_mail.send_email.call_args
            assert "Nueva propuesta" in call_args.kwargs["subject"]

    @patch("app.modules.community.services.url_for")
    @patch("app.modules.community.services.mail_manager")
    def test_send_approval_notification_calls_send_email(self, mock_mail, mock_url_for, test_client):
        """Test that approval notification calls send_email"""
        with test_client.application.app_context():
            mock_url_for.return_value = "http://localhost/test"
            mock_submission = self._create_mock_submission()

            NotificationService.send_approval_notification(mock_submission)

            mock_mail.send_email.assert_called_once()

    @patch("app.modules.community.services.url_for")
    @patch("app.modules.community.services.mail_manager")
    def test_send_approval_notification_correct_template(self, mock_mail, mock_url_for, test_client):
        """Test that approval notification uses correct template"""
        with test_client.application.app_context():
            mock_url_for.return_value = "http://localhost/test"
            mock_submission = self._create_mock_submission()

            NotificationService.send_approval_notification(mock_submission)

            call_args = mock_mail.send_email.call_args
            assert "dataset_accepted" in call_args.kwargs["template"]

    @patch("app.modules.community.services.url_for")
    @patch("app.modules.community.services.mail_manager")
    def test_send_rejection_notification_calls_send_email(self, mock_mail, mock_url_for, test_client):
        """Test that rejection notification calls send_email"""
        with test_client.application.app_context():
            mock_url_for.return_value = "http://localhost/test"
            mock_submission = self._create_mock_submission()

            NotificationService.send_rejection_notification(mock_submission)

            mock_mail.send_email.assert_called_once()

    @patch("app.modules.community.services.url_for")
    @patch("app.modules.community.services.mail_manager")
    def test_send_rejection_notification_includes_feedback(self, mock_mail, mock_url_for, test_client):
        """Test that rejection notification includes feedback in context"""
        with test_client.application.app_context():
            mock_url_for.return_value = "http://localhost/test"
            mock_submission = self._create_mock_submission()

            NotificationService.send_rejection_notification(mock_submission)

            call_args = mock_mail.send_email.call_args
            assert call_args.kwargs["context"]["feedback"] == "Test feedback"

    @patch("app.modules.community.services.url_for")
    @patch("app.modules.community.services.mail_manager")
    def test_send_new_submission_to_multiple_curators(self, mock_mail, mock_url_for, test_client):
        """Test that notification is sent to all curators and owners"""
        with test_client.application.app_context():
            mock_url_for.return_value = "http://localhost/test"
            mock_submission = self._create_mock_submission()

            curator1 = MagicMock()
            curator1.email = "curator1@example.com"
            curator2 = MagicMock()
            curator2.email = "curator2@example.com"
            owner = MagicMock()
            owner.email = "owner@example.com"

            mock_submission.community.get_curators.return_value = [curator1, curator2]
            mock_submission.community.get_owners.return_value = [owner]

            NotificationService.send_new_submission_notification(mock_submission)

            assert mock_mail.send_email.call_count == 3
