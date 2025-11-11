from typing import Optional, List
from datetime import datetime

from app import db
from app.modules.community.models import (
    Community, CommunityMembership, DatasetCommunitySubmission,
    SubmissionStatus, CommunityRole
)
from core.repositories.BaseRepository import BaseRepository


class CommunityRepository(BaseRepository):
    """Repository for Community operations"""
    
    def __init__(self):
        super().__init__(Community)
    
    def get_active_communities(self) -> List[Community]:
        """Get all active communities"""
        from app.modules.community.models import CommunityStatus
        return self.model.query.filter_by(status=CommunityStatus.ACTIVE).all()
    
    def get_by_name(self, name: str) -> Optional[Community]:
        """Get community by name"""
        return self.model.query.filter_by(name=name).first()


class DatasetCommunitySubmissionRepository(BaseRepository):
    """Repository for DatasetCommunitySubmission operations"""
    
    def __init__(self):
        super().__init__(DatasetCommunitySubmission)
    
    def create_submission(
        self, 
        dataset_id: int, 
        community_id: int
    ) -> Optional[DatasetCommunitySubmission]:
        """
        Create a new dataset submission to a community
        
        Args:
            dataset_id: ID of the dataset
            community_id: ID of the community
            
        Returns:
            DatasetCommunitySubmission instance or None if already exists
        """
        # Check if submission already exists
        existing = self.model.query.filter_by(
            dataset_id=dataset_id,
            community_id=community_id
        ).first()
        
        if existing:
            return None
        
        submission = self.model(
            dataset_id=dataset_id,
            community_id=community_id,
            status=SubmissionStatus.PENDING
        )
        
        db.session.add(submission)
        db.session.commit()
        
        return submission
    
    def accept_submission(
        self,
        submission_id: int,
        reviewer_id: int,
        review_notes: Optional[str] = None
    ) -> Optional[DatasetCommunitySubmission]:
        """
        Accept a dataset submission
        
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
        review_notes: Optional[str] = None
    ) -> Optional[DatasetCommunitySubmission]:
        """
        Reject a dataset submission
        
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
        
        submission.status = SubmissionStatus.REJECTED
        submission.reviewed_at = datetime.utcnow()
        submission.reviewed_by = reviewer_id
        submission.review_notes = review_notes
        
        db.session.commit()
        
        return submission
    
    def get_pending_submissions(self, community_id: int) -> List[DatasetCommunitySubmission]:
        """Get all pending submissions for a community"""
        return self.model.query.filter_by(
            community_id=community_id,
            status=SubmissionStatus.PENDING
        ).all()
    
    def get_submissions_by_dataset(self, dataset_id: int) -> List[DatasetCommunitySubmission]:
        """Get all submissions for a dataset"""
        return self.model.query.filter_by(dataset_id=dataset_id).all()


class CommunityMembershipRepository(BaseRepository):
    """Repository for CommunityMembership operations"""
    
    def __init__(self):
        super().__init__(CommunityMembership)
    
    def add_member(
        self,
        user_id: int,
        community_id: int,
        role: CommunityRole = CommunityRole.MEMBER
    ) -> Optional[CommunityMembership]:
        """
        Add a user to a community
        
        Args:
            user_id: ID of the user
            community_id: ID of the community
            role: Role of the user in the community
            
        Returns:
            CommunityMembership instance or None if already exists
        """
        existing = self.model.query.filter_by(
            user_id=user_id,
            community_id=community_id
        ).first()
        
        if existing:
            return None
        
        membership = self.model(
            user_id=user_id,
            community_id=community_id,
            role=role
        )
        
        db.session.add(membership)
        db.session.commit()
        
        return membership
    
    def is_curator(self, user_id: int, community_id: int) -> bool:
        """Check if user is a curator or owner of the community"""
        membership = self.model.query.filter_by(
            user_id=user_id,
            community_id=community_id
        ).first()
        
        if not membership:
            return False
        
        return membership.role in [CommunityRole.CURATOR, CommunityRole.OWNER]
    
    def get_user_communities(self, user_id: int) -> List[CommunityMembership]:
        """Get all communities a user is a member of"""
        return self.model.query.filter_by(user_id=user_id).all()