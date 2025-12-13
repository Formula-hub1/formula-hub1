import pytest

from app import db
from app.modules.auth.models import User
from app.modules.community.models import (
    CommunityMembership,
    CommunityRole,
    CommunityStatus,
)
from app.modules.community.repositories import (
    CommunityMembershipRepository,
    CommunityRepository,
)
from app.modules.profile.models import UserProfile


@pytest.fixture(scope="module")
def test_client(test_client):
    """
    Extends the test_client fixture for module testing.
    """
    with test_client.application.app_context():
        user = User.query.filter_by(email="test@example.com").first()
        if user and not user.profile:
            profile = UserProfile(user_id=user.id, name="Test", surname="User")
            db.session.add(profile)
            db.session.commit()

    yield test_client


# ============================================================================
# COMMUNITY REPOSITORY TESTS
# ============================================================================


def test_community_repository_create_with_owner(test_client):
    """Test creating a community with owner"""
    with test_client.application.app_context():
        repo = CommunityRepository()
        user = User.query.filter_by(email="test@example.com").first()

        community = repo.create_with_owner(
            name="Test Community",
            slug="test-community",
            owner_id=user.id,
            description="A test community",
            is_public=True,
        )

        assert community is not None
        assert community.name == "Test Community"
        assert community.slug == "test-community"
        assert community.is_public is True
        assert community.status == CommunityStatus.ACTIVE

        membership = CommunityMembership.query.filter_by(community_id=community.id, user_id=user.id).first()
        assert membership is not None
        assert membership.role == CommunityRole.OWNER

        db.session.delete(community)
        db.session.commit()


def test_community_repository_create_duplicate_slug(test_client):
    """Test that duplicate slugs return None"""
    with test_client.application.app_context():
        repo = CommunityRepository()
        user = User.query.filter_by(email="test@example.com").first()

        community1 = repo.create_with_owner(
            name="First Community",
            slug="duplicate-slug",
            owner_id=user.id,
        )

        community2 = repo.create_with_owner(
            name="Second Community",
            slug="duplicate-slug",
            owner_id=user.id,
        )

        assert community1 is not None
        assert community2 is None

        db.session.delete(community1)
        db.session.commit()


def test_community_repository_get_by_slug(test_client):
    """Test getting community by slug"""
    with test_client.application.app_context():
        repo = CommunityRepository()
        user = User.query.filter_by(email="test@example.com").first()

        community = repo.create_with_owner(
            name="Slug Test",
            slug="slug-test",
            owner_id=user.id,
        )

        found = repo.get_by_slug("slug-test")
        assert found is not None
        assert found.id == community.id

        not_found = repo.get_by_slug("nonexistent-slug")
        assert not_found is None

        db.session.delete(community)
        db.session.commit()


def test_community_repository_get_public_communities(test_client):
    """Test getting public communities"""
    with test_client.application.app_context():
        repo = CommunityRepository()
        user = User.query.filter_by(email="test@example.com").first()

        public = repo.create_with_owner(
            name="Public Community",
            slug="public-comm",
            owner_id=user.id,
            is_public=True,
        )

        private = repo.create_with_owner(
            name="Private Community",
            slug="private-comm",
            owner_id=user.id,
            is_public=False,
        )

        public_communities = repo.get_public_communities()
        public_ids = [c.id for c in public_communities]

        assert public.id in public_ids
        assert private.id not in public_ids

        db.session.delete(public)
        db.session.delete(private)
        db.session.commit()


def test_community_repository_update(test_client):
    """Test updating a community"""
    with test_client.application.app_context():
        repo = CommunityRepository()
        user = User.query.filter_by(email="test@example.com").first()

        community = repo.create_with_owner(
            name="Original Name",
            slug="update-test",
            owner_id=user.id,
        )

        updated = repo.update(
            community.id,
            name="Updated Name",
            description="New description",
        )

        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.description == "New description"

        db.session.delete(community)
        db.session.commit()


def test_community_repository_delete(test_client):
    """Test deleting a community"""
    with test_client.application.app_context():
        repo = CommunityRepository()
        user = User.query.filter_by(email="test@example.com").first()

        community = repo.create_with_owner(
            name="To Delete",
            slug="to-delete",
            owner_id=user.id,
        )
        community_id = community.id

        result = repo.delete(community_id)
        assert result is True

        deleted = repo.get_by_id(community_id)
        assert deleted is None


def test_community_repository_search(test_client):
    """Test searching communities"""
    with test_client.application.app_context():
        repo = CommunityRepository()
        user = User.query.filter_by(email="test@example.com").first()

        community = repo.create_with_owner(
            name="Machine Learning Research",
            slug="ml-research",
            owner_id=user.id,
            description="Research on ML models",
            is_public=True,
        )

        results = repo.search("Machine")
        assert len(results) >= 1
        assert any(c.id == community.id for c in results)

        results = repo.search("ML models")
        assert len(results) >= 1

        results = repo.search("xyznonexistent")
        assert len(results) == 0

        db.session.delete(community)
        db.session.commit()


# ============================================================================
# MEMBERSHIP REPOSITORY TESTS
# ============================================================================


def test_membership_repository_add_member(test_client):
    """Test adding a member to a community"""
    with test_client.application.app_context():
        community_repo = CommunityRepository()
        membership_repo = CommunityMembershipRepository()

        user = User.query.filter_by(email="test@example.com").first()

        user2 = User(email="member@example.com", password="test1234")
        db.session.add(user2)
        db.session.commit()

        community = community_repo.create_with_owner(
            name="Member Test",
            slug="member-test",
            owner_id=user.id,
        )

        membership = membership_repo.add_member(
            community_id=community.id,
            user_id=user2.id,
            role="member",
        )

        assert membership is not None
        assert membership.role == CommunityRole.MEMBER

        db.session.delete(community)
        db.session.delete(user2)
        db.session.commit()


def test_membership_repository_add_duplicate_member(test_client):
    """Test that adding duplicate member returns None"""
    with test_client.application.app_context():
        community_repo = CommunityRepository()
        membership_repo = CommunityMembershipRepository()

        user = User.query.filter_by(email="test@example.com").first()

        community = community_repo.create_with_owner(
            name="Duplicate Test",
            slug="duplicate-member-test",
            owner_id=user.id,
        )

        duplicate = membership_repo.add_member(
            community_id=community.id,
            user_id=user.id,
            role="member",
        )

        assert duplicate is None

        db.session.delete(community)
        db.session.commit()


def test_membership_repository_remove_member(test_client):
    """Test removing a member from a community"""
    with test_client.application.app_context():
        community_repo = CommunityRepository()
        membership_repo = CommunityMembershipRepository()

        user = User.query.filter_by(email="test@example.com").first()
        user2 = User(email="toremove@example.com", password="test1234")
        db.session.add(user2)
        db.session.commit()

        community = community_repo.create_with_owner(
            name="Remove Test",
            slug="remove-test",
            owner_id=user.id,
        )

        membership_repo.add_member(community.id, user2.id, "member")

        result = membership_repo.remove_member(community.id, user2.id)
        assert result is True

        is_member = membership_repo.is_member(community.id, user2.id)
        assert is_member is False

        db.session.delete(community)
        db.session.delete(user2)
        db.session.commit()


def test_membership_repository_is_curator_or_owner(test_client):
    """Test checking curator/owner status"""
    with test_client.application.app_context():
        community_repo = CommunityRepository()
        membership_repo = CommunityMembershipRepository()

        user = User.query.filter_by(email="test@example.com").first()
        curator = User(email="curator@example.com", password="test1234")
        member = User(email="member2@example.com", password="test1234")
        db.session.add(curator)
        db.session.add(member)
        db.session.commit()

        community = community_repo.create_with_owner(
            name="Role Test",
            slug="role-test",
            owner_id=user.id,
        )

        membership_repo.add_member(community.id, curator.id, "curator")
        membership_repo.add_member(community.id, member.id, "member")

        is_owner = membership_repo.is_curator_or_owner(community.id, user.id)
        assert is_owner is True

        is_curator = membership_repo.is_curator_or_owner(community.id, curator.id)
        assert is_curator is True

        is_regular = membership_repo.is_curator_or_owner(community.id, member.id)
        assert is_regular is False

        db.session.delete(community)
        db.session.delete(curator)
        db.session.delete(member)
        db.session.commit()


def test_membership_repository_update_role(test_client):
    """Test updating a member's role"""
    with test_client.application.app_context():
        community_repo = CommunityRepository()
        membership_repo = CommunityMembershipRepository()

        user = User.query.filter_by(email="test@example.com").first()
        user2 = User(email="rolechange@example.com", password="test1234")
        db.session.add(user2)
        db.session.commit()

        community = community_repo.create_with_owner(
            name="Role Update Test",
            slug="role-update-test",
            owner_id=user.id,
        )

        membership_repo.add_member(community.id, user2.id, "member")

        result = membership_repo.update_role(community.id, user2.id, "curator")
        assert result is True

        is_curator = membership_repo.is_curator_or_owner(community.id, user2.id)
        assert is_curator is True

        db.session.delete(community)
        db.session.delete(user2)
        db.session.commit()


def test_membership_repository_get_community_members(test_client):
    """Test getting all members of a community"""
    with test_client.application.app_context():
        community_repo = CommunityRepository()
        membership_repo = CommunityMembershipRepository()

        user = User.query.filter_by(email="test@example.com").first()
        user2 = User(email="getmembers@example.com", password="test1234")
        db.session.add(user2)
        db.session.commit()

        community = community_repo.create_with_owner(
            name="Get Members Test",
            slug="get-members-test",
            owner_id=user.id,
        )

        membership_repo.add_member(community.id, user2.id, "member")

        members = membership_repo.get_community_members(community.id)
        assert len(members) == 2

        owners = membership_repo.get_community_members(community.id, role="owner")
        assert len(owners) == 1

        db.session.delete(community)
        db.session.delete(user2)
        db.session.commit()
