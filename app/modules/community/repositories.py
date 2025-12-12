from datetime import datetime
from typing import List, Optional

from app import db
from app.modules.community.models import (
    Community,
    CommunityMembership,
    CommunityRole,
    CommunityStatus,
    DatasetCommunitySubmission,
    SubmissionStatus,
)
from core.repositories.BaseRepository import BaseRepository


class CommunityRepository(BaseRepository):
    """Repository for Community operations"""

    def __init__(self):
        super().__init__(Community)

    def get_active_communities(self) -> List[Community]:
        """Get all active communities"""
        return self.model.query.filter_by(status=CommunityStatus.ACTIVE).all()

    def get_by_name(self, name: str) -> Optional[Community]:
        """Get community by name"""
        return self.model.query.filter_by(name=name).first()

    def get_by_slug(self, slug: str) -> Optional[Community]:
        """Get community by slug"""
        return self.model.query.filter_by(slug=slug).first()

    def get_public_communities(self) -> List[Community]:
        """Get all public and active communities"""
        return self.model.query.filter_by(is_public=True, status=CommunityStatus.ACTIVE).all()

    def get_user_communities(self, user_id: int) -> List[Community]:
        """Get all communities where user is a member"""
        return self.model.query.join(CommunityMembership).filter(CommunityMembership.user_id == user_id).all()

    def search(self, query: str) -> List[Community]:
        """Search communities by name or description"""
        search_term = f"%{query}%"
        return (
            self.model.query.filter(
                db.or_(
                    self.model.name.ilike(search_term),
                    self.model.description.ilike(search_term),
                )
            )
            .filter_by(is_public=True, status=CommunityStatus.ACTIVE)
            .all()
        )

    def create_with_owner(self, name: str, slug: str, owner_id: int, **kwargs) -> Optional[Community]:
        """
        Create a new community with an owner

        Args:
            name: Name of the community
            slug: URL slug for the community
            owner_id: ID of the user who will be the owner
            **kwargs: Additional fields (description, logo_url, website, is_public)

        Returns:
            Community instance or None if slug already exists
        """
        # Check if slug already exists
        existing = self.get_by_slug(slug)
        if existing:
            return None

        # Create community
        community = self.model(
            name=name,
            slug=slug,
            description=kwargs.get("description"),
            logo_url=kwargs.get("logo_url"),
            website=kwargs.get("website"),
            is_public=kwargs.get("is_public", True),
            status=CommunityStatus.ACTIVE,
        )

        db.session.add(community)
        db.session.flush()  # Get the community ID

        # Add owner as member
        membership = CommunityMembership(
            user_id=owner_id,
            community_id=community.id,
            role=CommunityRole.OWNER,
        )
        db.session.add(membership)
        db.session.commit()

        return community

    def update(self, community_id: int, **kwargs) -> Optional[Community]:
        """Update community fields"""
        community = self.get_by_id(community_id)
        if not community:
            return None

        for key, value in kwargs.items():
            if hasattr(community, key) and key != "id":
                setattr(community, key, value)

        db.session.commit()
        return community

    def delete(self, community_id: int) -> bool:
        """Delete a community"""
        community = self.get_by_id(community_id)
        if not community:
            return False

        db.session.delete(community)
        db.session.commit()
        return True


class CommunityMembershipRepository(BaseRepository):
    """Repository for CommunityMembership operations"""

    def __init__(self):
        super().__init__(CommunityMembership)

    def add_member(self, community_id: int, user_id: int, role: str = "member") -> Optional[CommunityMembership]:
        """
        Add a user to a community

        Args:
            community_id: ID of the community
            user_id: ID of the user
            role: Role string ('member', 'curator', 'owner')

        Returns:
            CommunityMembership instance or None if already exists
        """
        existing = self.model.query.filter_by(user_id=user_id, community_id=community_id).first()

        if existing:
            return None

        # Convert string role to enum
        role_enum = CommunityRole(role) if isinstance(role, str) else role

        membership = self.model(user_id=user_id, community_id=community_id, role=role_enum)

        db.session.add(membership)
        db.session.commit()

        return membership

    def remove_member(self, community_id: int, user_id: int) -> bool:
        """Remove a member from a community"""
        membership = self.model.query.filter_by(community_id=community_id, user_id=user_id).first()

        if not membership:
            return False

        db.session.delete(membership)
        db.session.commit()
        return True

    def update_role(self, community_id: int, user_id: int, new_role: str) -> bool:
        """Update a member's role"""
        membership = self.model.query.filter_by(community_id=community_id, user_id=user_id).first()

        if not membership:
            return False

        membership.role = CommunityRole(new_role)
        db.session.commit()
        return True

    def is_member(self, community_id: int, user_id: int) -> bool:
        """Check if user is a member of the community"""
        membership = self.model.query.filter_by(user_id=user_id, community_id=community_id).first()
        return membership is not None

    def is_curator_or_owner(self, community_id: int, user_id: int) -> bool:
        """Check if user is a curator or owner of the community"""
        membership = self.model.query.filter_by(user_id=user_id, community_id=community_id).first()

        if not membership:
            return False

        return membership.role in [CommunityRole.CURATOR, CommunityRole.OWNER]

    def get_community_members(self, community_id: int, role: Optional[str] = None) -> List[CommunityMembership]:
        """Get all members of a community, optionally filtered by role"""
        query = self.model.query.filter_by(community_id=community_id)

        if role:
            query = query.filter_by(role=CommunityRole(role))

        return query.all()

    def get_user_communities(self, user_id: int) -> List[CommunityMembership]:
        """Get all communities a user is a member of"""
        return self.model.query.filter_by(user_id=user_id).all()


class DatasetCommunitySubmissionRepository(BaseRepository):
    """Repository for DatasetCommunitySubmission operations"""

    def __init__(self):
        super().__init__(DatasetCommunitySubmission)

    def submit_dataset(
        self,
        dataset_id: int,
        community_id: int,
        submitter_id: int,
        message: Optional[str] = None,
    ) -> Optional[DatasetCommunitySubmission]:
        """
        Submit a dataset to a community

        Args:
            dataset_id: ID of the dataset
            community_id: ID of the community
            submitter_id: ID of the user submitting
            message: Optional message from submitter

        Returns:
            DatasetCommunitySubmission instance or None if already exists
        """
        # Check if submission already exists
        existing = self.model.query.filter_by(dataset_id=dataset_id, community_id=community_id).first()

        if existing:
            return None

        submission = self.model(
            dataset_id=dataset_id,
            community_id=community_id,
            submitter_id=submitter_id,
            message=message,
            status=SubmissionStatus.PENDING,
        )

        db.session.add(submission)
        db.session.commit()

        return submission

    def create_submission(self, dataset_id: int, community_id: int) -> Optional[DatasetCommunitySubmission]:
        """
        Create a new dataset submission to a community (legacy method)
        """
        return self.submit_dataset(dataset_id, community_id, submitter_id=0)

    def approve_submission(
        self, submission_id: int, reviewer_id: int, review_notes: Optional[str] = None
    ) -> Optional[DatasetCommunitySubmission]:
        """
        Approve a dataset submission

        Args:
            submission_id: ID of the submission
            reviewer_id: ID of the user reviewing
            review_notes: Optional notes from reviewer

        Returns:
            Updated DatasetCommunitySubmission instance
        """
        submission = self.get_by_id(submission_id)

        if not submission:
            return None

        submission.status = SubmissionStatus.ACCEPTED
        submission.reviewed_at = datetime.utcnow()
        submission.reviewed_by = reviewer_id
        submission.review_notes = review_notes

        db.session.commit()

        return submission

    def reject_submission(
        self,
        submission_id: int,
        reviewer_id: int,
        feedback: Optional[str] = None,
    ) -> Optional[DatasetCommunitySubmission]:
        """
        Reject a dataset submission

        Args:
            submission_id: ID of the submission
            reviewer_id: ID of the user reviewing
            feedback: Feedback for the submitter

        Returns:
            Updated DatasetCommunitySubmission instance
        """
        submission = self.get_by_id(submission_id)

        if not submission:
            return None

        submission.status = SubmissionStatus.REJECTED
        submission.reviewed_at = datetime.utcnow()
        submission.reviewed_by = reviewer_id
        submission.feedback = feedback

        db.session.commit()

        return submission

    def get_pending_submissions(self, community_id: int) -> List[DatasetCommunitySubmission]:
        """Get all pending submissions for a community"""
        return self.model.query.filter_by(community_id=community_id, status=SubmissionStatus.PENDING).all()

    def get_approved_submissions(self, community_id: int) -> List[DatasetCommunitySubmission]:
        """Get all approved submissions for a community"""
        return self.model.query.filter_by(community_id=community_id, status=SubmissionStatus.ACCEPTED).all()

    def get_user_submissions(self, user_id: int, status: Optional[str] = None) -> List[DatasetCommunitySubmission]:
        """Get all submissions by a user, optionally filtered by status"""
        query = self.model.query.filter_by(submitter_id=user_id)

        if status:
            query = query.filter_by(status=SubmissionStatus(status))

        return query.all()

    def get_submissions_by_dataset(self, dataset_id: int) -> List[DatasetCommunitySubmission]:
        """Get all submissions for a dataset"""
        return self.model.query.filter_by(dataset_id=dataset_id).all()
