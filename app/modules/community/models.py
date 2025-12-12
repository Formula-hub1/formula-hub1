from datetime import datetime
from enum import Enum

from sqlalchemy import Enum as SQLAlchemyEnum

from app import db


class CommunityStatus(Enum):
    """Status of a community"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class Community(db.Model):
    """Community model - thematic or institutional space grouping datasets"""

    __tablename__ = "community"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    slug = db.Column(db.String(255), nullable=False, unique=True)  # URL amigable
    description = db.Column(db.Text)
    logo_url = db.Column(db.String(500), nullable=True)  # URL del logo
    website = db.Column(db.String(500), nullable=True)  # Sitio web
    is_public = db.Column(db.Boolean, default=True)  # Visibilidad
    status = db.Column(SQLAlchemyEnum(CommunityStatus), default=CommunityStatus.ACTIVE)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Relationships
    memberships = db.relationship("CommunityMembership", back_populates="community", cascade="all, delete-orphan")
    dataset_submissions = db.relationship(
        "DatasetCommunitySubmission", back_populates="community", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Community {self.name}>"

    def get_owners(self):
        """Get all owners of this community"""
        return [m.user for m in self.memberships if m.role == CommunityRole.OWNER]

    def get_curators(self):
        """Get all curators of this community"""
        return [m.user for m in self.memberships if m.role == CommunityRole.CURATOR]

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "logo_url": self.logo_url,
            "website": self.website,
            "is_public": self.is_public,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class CommunityRole(Enum):
    """Roles within a community"""

    OWNER = "owner"
    CURATOR = "curator"  # Same as moderator
    MEMBER = "member"


class CommunityMembership(db.Model):
    """Association table for users and communities with roles"""

    __tablename__ = "community_membership"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    community_id = db.Column(db.Integer, db.ForeignKey("community.id"), nullable=False)
    role = db.Column(SQLAlchemyEnum(CommunityRole), default=CommunityRole.MEMBER)
    joined_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    user = db.relationship("User", backref="community_memberships")
    community = db.relationship("Community", back_populates="memberships")

    # Unique constraint to prevent duplicate memberships
    __table_args__ = (db.UniqueConstraint("user_id", "community_id", name="unique_user_community"),)

    def __repr__(self):
        return f"<CommunityMembership user_id={self.user_id} community_id={self.community_id}>"


class SubmissionStatus(Enum):
    """Status of a dataset submission to a community"""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class DatasetCommunitySubmission(db.Model):
    """Tracks dataset submissions (proposals) to communities"""

    __tablename__ = "dataset_community_submission"

    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey("dataset.id"), nullable=False)
    community_id = db.Column(db.Integer, db.ForeignKey("community.id"), nullable=False)
    submitter_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)  # Quién propuso
    message = db.Column(db.Text, nullable=True)  # Mensaje del submitter
    status = db.Column(SQLAlchemyEnum(SubmissionStatus), default=SubmissionStatus.PENDING)
    submitted_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)
    reviewed_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    review_notes = db.Column(db.Text)
    feedback = db.Column(db.Text, nullable=True)  # Feedback del curador

    # Relationships
    dataset = db.relationship("DataSet", backref="community_submissions")
    community = db.relationship("Community", back_populates="dataset_submissions")
    submitter = db.relationship("User", foreign_keys=[submitter_id], backref="submitted_datasets")
    reviewer = db.relationship("User", foreign_keys=[reviewed_by])

    # Unique constraint to prevent duplicate submissions
    __table_args__ = (db.UniqueConstraint("dataset_id", "community_id", name="unique_dataset_community"),)

    def __repr__(self):
        return (
            f"<DatasetCommunitySubmission dataset_id={self.dataset_id} "
            f"community_id={self.community_id} status={self.status.value}>"
        )

    def to_dict(self):
        return {
            "id": self.id,
            "dataset_id": self.dataset_id,
            "community_id": self.community_id,
            "submitter_id": self.submitter_id,
            "message": self.message,
            "status": self.status.value,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "reviewed_by": self.reviewed_by,
            "review_notes": self.review_notes,
            "feedback": self.feedback,
        }
