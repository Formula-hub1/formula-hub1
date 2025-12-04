"""
Community services - Business logic layer
"""

from typing import List, Optional

from flask import current_app, url_for

from app.modules.community.models import Community, CommunityMembership, DatasetCommunitySubmission
from app.modules.community.repositories import (
    CommunityMembershipRepository,
    CommunityRepository,
    DatasetCommunitySubmissionRepository,
)
from core.managers.mail_manager import mail_manager


class CommunityService:
    """Service for community operations"""

    def __init__(self):
        self.community_repo = CommunityRepository()
        self.membership_repo = CommunityMembershipRepository()
        self.submission_repo = DatasetCommunitySubmissionRepository()

    def create_community(self, name: str, slug: str, owner_id: int, **kwargs) -> Optional[Community]:
        """Create a new community with owner"""
        return self.community_repo.create_with_owner(name, slug, owner_id, **kwargs)

    def get_community(self, community_id: int) -> Optional[Community]:
        """Get community by ID"""
        return self.community_repo.get_by_id(community_id)

    def get_community_by_slug(self, slug: str) -> Optional[Community]:
        """Get community by slug"""
        return self.community_repo.get_by_slug(slug)

    def list_public_communities(self) -> List[Community]:
        """List all public communities"""
        return self.community_repo.get_public_communities()

    def get_user_communities(self, user_id: int) -> List[Community]:
        """Get all communities where user is a member"""
        return self.community_repo.get_user_communities(user_id)

    def search_communities(self, query: str) -> List[Community]:
        """Search communities"""
        return self.community_repo.search(query)

    def update_community(self, community_id: int, **kwargs) -> Optional[Community]:
        """Update community"""
        return self.community_repo.update(community_id, **kwargs)

    def delete_community(self, community_id: int) -> bool:
        """Delete community"""
        return self.community_repo.delete(community_id)

    # Member management
    def add_member(self, community_id: int, user_id: int, role: str = "member") -> Optional[CommunityMembership]:
        """Add a member to a community"""
        return self.membership_repo.add_member(community_id, user_id, role)

    def remove_member(self, community_id: int, user_id: int) -> bool:
        """Remove a member from a community"""
        return self.membership_repo.remove_member(community_id, user_id)

    def update_member_role(self, community_id: int, user_id: int, new_role: str) -> bool:
        """Update member role"""
        return self.membership_repo.update_role(community_id, user_id, new_role)

    def get_community_members(self, community_id: int, role: Optional[str] = None) -> List[CommunityMembership]:
        """Get community members"""
        return self.membership_repo.get_community_members(community_id, role)

    def is_member(self, community_id: int, user_id: int) -> bool:
        """Check if user is a member"""
        return self.membership_repo.is_member(community_id, user_id)

    def is_curator_or_owner(self, community_id: int, user_id: int) -> bool:
        """Check if user can manage the community"""
        return self.membership_repo.is_curator_or_owner(community_id, user_id)

    # Dataset submissions
    def submit_dataset(
        self, dataset_id: int, community_id: int, submitter_id: int, message: Optional[str] = None
    ) -> Optional[DatasetCommunitySubmission]:
        """Submit a dataset to a community"""
        submission = self.submission_repo.submit_dataset(dataset_id, community_id, submitter_id, message)

        if submission:
            # Send notification to curators
            NotificationService.send_new_submission_notification(submission)

        return submission

    def approve_submission(self, submission_id: int, reviewer_id: int) -> Optional[DatasetCommunitySubmission]:
        """Approve a dataset submission"""
        submission = self.submission_repo.approve_submission(submission_id, reviewer_id)

        if submission:
            # Send approval notification to submitter
            NotificationService.send_approval_notification(submission)

        return submission

    def reject_submission(
        self, submission_id: int, reviewer_id: int, feedback: str
    ) -> Optional[DatasetCommunitySubmission]:
        """Reject a dataset submission"""
        submission = self.submission_repo.reject_submission(submission_id, reviewer_id, feedback)

        if submission:
            # Send rejection notification to submitter
            NotificationService.send_rejection_notification(submission)

        return submission

    def get_pending_submissions(self, community_id: int) -> List[DatasetCommunitySubmission]:
        """Get pending submissions for a community"""
        return self.submission_repo.get_pending_submissions(community_id)

    def get_approved_datasets(self, community_id: int) -> List[DatasetCommunitySubmission]:
        """Get approved datasets for a community"""
        return self.submission_repo.get_approved_submissions(community_id)

    def get_user_submissions(self, user_id: int, status: Optional[str] = None) -> List[DatasetCommunitySubmission]:
        """Get user submissions"""
        return self.submission_repo.get_user_submissions(user_id, status)


class NotificationService:
    """Service for sending email notifications"""

    @staticmethod
    def send_new_submission_notification(submission: DatasetCommunitySubmission):
        """Send notification to curators when a new dataset is submitted"""
        try:
            community = submission.community
            dataset = submission.dataset
            submitter = submission.submitter

            # Get all curators and owners
            curators = community.get_curators() + community.get_owners()

            if not curators:
                current_app.logger.warning(f"No curators found for community {community.id}")
                return

            # Prepare email data
            subject = f"Nueva propuesta de dataset en {community.name}"

            # Get dataset title from metadata
            dataset_title = "Sin título"
            if hasattr(dataset, "ds_meta_data") and dataset.ds_meta_data:
                dataset_title = dataset.ds_meta_data.title or dataset_title

            context = {
                "community_name": community.name,
                "dataset_title": dataset_title,
                "submitter_name": submitter.profile.name if hasattr(submitter, "profile") else submitter.email,
                "submission_message": submission.message or "",
                "submission_url": url_for("community.review_submission", submission_id=submission.id, _external=True),
                "community_url": url_for("community.detail", slug=community.slug, _external=True),
            }

            # Send to all curators
            for curator in curators:
                mail_manager.send_email(
                    to=curator.email, subject=subject, template="emails/new_submission", context=context
                )

            current_app.logger.info(f"New submission notification sent for submission {submission.id}")

        except Exception as e:
            current_app.logger.error(f"Error sending new submission notification: {str(e)}")

    @staticmethod
    def send_approval_notification(submission: DatasetCommunitySubmission):
        """Send notification to dataset owner when submission is approved"""
        try:
            community = submission.community
            dataset = submission.dataset
            submitter = submission.submitter
            reviewer = submission.reviewer

            # Prepare email data
            subject = f"¡Dataset aceptado en {community.name}!"

            # Get dataset title from metadata
            dataset_title = "Sin título"
            if hasattr(dataset, "ds_meta_data") and dataset.ds_meta_data:
                dataset_title = dataset.ds_meta_data.title or dataset_title

            reviewer_name = "Un curador"
            if reviewer and hasattr(reviewer, "profile"):
                reviewer_name = reviewer.profile.name if reviewer.profile else reviewer.email

            context = {
                "community_name": community.name,
                "dataset_title": dataset_title,
                "reviewer_name": reviewer_name,
                "dataset_url": url_for("dataset.view", dataset_id=dataset.id, _external=True),
                "community_url": url_for("community.detail", slug=community.slug, _external=True),
            }

            mail_manager.send_email(
                to=submitter.email, subject=subject, template="emails/dataset_accepted", context=context
            )

            current_app.logger.info(f"Approval notification sent for submission {submission.id}")

        except Exception as e:
            current_app.logger.error(f"Error sending approval notification: {str(e)}")

    @staticmethod
    def send_rejection_notification(submission: DatasetCommunitySubmission):
        """Send notification to dataset owner when submission is rejected"""
        try:
            community = submission.community
            dataset = submission.dataset
            submitter = submission.submitter
            reviewer = submission.reviewer

            # Prepare email data
            subject = f"Actualización sobre tu propuesta en {community.name}"

            # Get dataset title from metadata
            dataset_title = "Sin título"
            if hasattr(dataset, "ds_meta_data") and dataset.ds_meta_data:
                dataset_title = dataset.ds_meta_data.title or dataset_title

            reviewer_name = "Un curador"
            if reviewer and hasattr(reviewer, "profile"):
                reviewer_name = reviewer.profile.name if reviewer.profile else reviewer.email

            context = {
                "community_name": community.name,
                "dataset_title": dataset_title,
                "reviewer_name": reviewer_name,
                "feedback": submission.feedback or "No se proporcionó feedback adicional.",
                "dataset_url": url_for("dataset.view", dataset_id=dataset.id, _external=True),
                "community_url": url_for("community.detail", slug=community.slug, _external=True),
            }

            mail_manager.send_email(
                to=submitter.email, subject=subject, template="emails/dataset_rejected", context=context
            )

            current_app.logger.info(f"Rejection notification sent for submission {submission.id}")

        except Exception as e:
            current_app.logger.error(f"Error sending rejection notification: {str(e)}")


# Singleton instances
community_service = CommunityService()
notification_service = NotificationService()
