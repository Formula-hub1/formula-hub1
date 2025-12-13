import pytest

from app import db
from app.modules.auth.models import User
from app.modules.community.services import CommunityService
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
# COMMUNITY SERVICE TESTS
# ============================================================================


def test_community_service_create(test_client):
    """Test community service create"""
    with test_client.application.app_context():
        service = CommunityService()
        user = User.query.filter_by(email="test@example.com").first()

        community = service.create_community(
            name="Service Test Community",
            slug="service-test-community",
            owner_id=user.id,
            description="Created via service",
        )

        assert community is not None
        assert community.name == "Service Test Community"

        db.session.delete(community)
        db.session.commit()


def test_community_service_create_duplicate(test_client):
    """Test community service create with duplicate slug"""
    with test_client.application.app_context():
        service = CommunityService()
        user = User.query.filter_by(email="test@example.com").first()

        community1 = service.create_community(
            name="Service Dup 1",
            slug="service-dup-test",
            owner_id=user.id,
        )

        community2 = service.create_community(
            name="Service Dup 2",
            slug="service-dup-test",
            owner_id=user.id,
        )

        assert community1 is not None
        assert community2 is None

        db.session.delete(community1)
        db.session.commit()


def test_community_service_get_by_slug(test_client):
    """Test community service get_community_by_slug"""
    with test_client.application.app_context():
        service = CommunityService()
        user = User.query.filter_by(email="test@example.com").first()

        community = service.create_community(
            name="Get By Slug Test",
            slug="get-by-slug-test",
            owner_id=user.id,
        )

        found = service.get_community_by_slug("get-by-slug-test")
        assert found is not None
        assert found.id == community.id

        not_found = service.get_community_by_slug("nonexistent")
        assert not_found is None

        db.session.delete(community)
        db.session.commit()


def test_community_service_is_member(test_client):
    """Test community service is_member check"""
    with test_client.application.app_context():
        service = CommunityService()
        user = User.query.filter_by(email="test@example.com").first()

        community = service.create_community(
            name="Member Check Test",
            slug="member-check-test",
            owner_id=user.id,
        )

        assert service.is_member(community.id, user.id) is True
        assert service.is_member(community.id, 99999) is False

        db.session.delete(community)
        db.session.commit()


def test_community_service_is_curator_or_owner(test_client):
    """Test community service is_curator_or_owner check"""
    with test_client.application.app_context():
        service = CommunityService()
        user = User.query.filter_by(email="test@example.com").first()

        user2 = User(email="svc-curator@example.com", password="test1234")
        user3 = User(email="svc-member@example.com", password="test1234")
        db.session.add(user2)
        db.session.add(user3)
        db.session.commit()

        community = service.create_community(
            name="Curator Check Test",
            slug="curator-check-test",
            owner_id=user.id,
        )

        service.add_member(community.id, user2.id, "curator")
        service.add_member(community.id, user3.id, "member")

        assert service.is_curator_or_owner(community.id, user.id) is True
        assert service.is_curator_or_owner(community.id, user2.id) is True
        assert service.is_curator_or_owner(community.id, user3.id) is False

        db.session.delete(community)
        db.session.delete(user2)
        db.session.delete(user3)
        db.session.commit()


def test_community_service_list_public(test_client):
    """Test listing public communities"""
    with test_client.application.app_context():
        service = CommunityService()
        user = User.query.filter_by(email="test@example.com").first()

        public = service.create_community(
            name="Public Service Test",
            slug="public-service-test",
            owner_id=user.id,
            is_public=True,
        )

        private = service.create_community(
            name="Private Service Test",
            slug="private-service-test",
            owner_id=user.id,
            is_public=False,
        )

        communities = service.list_public_communities()
        community_ids = [c.id for c in communities]

        assert public.id in community_ids
        assert private.id not in community_ids

        db.session.delete(public)
        db.session.delete(private)
        db.session.commit()


def test_community_service_search(test_client):
    """Test searching communities via service"""
    with test_client.application.app_context():
        service = CommunityService()
        user = User.query.filter_by(email="test@example.com").first()

        community = service.create_community(
            name="Searchable Community",
            slug="searchable-community",
            owner_id=user.id,
            description="This is a searchable test community",
            is_public=True,
        )

        results = service.search_communities("Searchable")
        assert len(results) >= 1
        assert any(c.id == community.id for c in results)

        db.session.delete(community)
        db.session.commit()


def test_community_service_update(test_client):
    """Test updating community via service"""
    with test_client.application.app_context():
        service = CommunityService()
        user = User.query.filter_by(email="test@example.com").first()

        community = service.create_community(
            name="Update Service Test",
            slug="update-service-test",
            owner_id=user.id,
        )

        updated = service.update_community(
            community.id,
            name="Updated Service Name",
            description="Updated description",
        )

        assert updated is not None
        assert updated.name == "Updated Service Name"
        assert updated.description == "Updated description"

        db.session.delete(community)
        db.session.commit()


def test_community_service_delete(test_client):
    """Test deleting community via service"""
    with test_client.application.app_context():
        service = CommunityService()
        user = User.query.filter_by(email="test@example.com").first()

        community = service.create_community(
            name="Delete Service Test",
            slug="delete-service-test",
            owner_id=user.id,
        )
        community_id = community.id

        result = service.delete_community(community_id)
        assert result is True

        deleted = service.get_community(community_id)
        assert deleted is None


# ============================================================================
# MEMBER MANAGEMENT SERVICE TESTS
# ============================================================================


def test_community_service_add_member(test_client):
    """Test adding member via service"""
    with test_client.application.app_context():
        service = CommunityService()
        user = User.query.filter_by(email="test@example.com").first()

        user2 = User(email="svc-add-member@example.com", password="test1234")
        db.session.add(user2)
        db.session.commit()

        community = service.create_community(
            name="Add Member Service Test",
            slug="add-member-service-test",
            owner_id=user.id,
        )

        membership = service.add_member(community.id, user2.id, "member")
        assert membership is not None

        assert service.is_member(community.id, user2.id) is True

        db.session.delete(community)
        db.session.delete(user2)
        db.session.commit()


def test_community_service_remove_member(test_client):
    """Test removing member via service"""
    with test_client.application.app_context():
        service = CommunityService()
        user = User.query.filter_by(email="test@example.com").first()

        user2 = User(email="svc-remove-member@example.com", password="test1234")
        db.session.add(user2)
        db.session.commit()

        community = service.create_community(
            name="Remove Member Service Test",
            slug="remove-member-service-test",
            owner_id=user.id,
        )

        service.add_member(community.id, user2.id, "member")
        result = service.remove_member(community.id, user2.id)

        assert result is True
        assert service.is_member(community.id, user2.id) is False

        db.session.delete(community)
        db.session.delete(user2)
        db.session.commit()


def test_community_service_update_member_role(test_client):
    """Test updating member role via service"""
    with test_client.application.app_context():
        service = CommunityService()
        user = User.query.filter_by(email="test@example.com").first()

        user2 = User(email="svc-update-role@example.com", password="test1234")
        db.session.add(user2)
        db.session.commit()

        community = service.create_community(
            name="Update Role Service Test",
            slug="update-role-service-test",
            owner_id=user.id,
        )

        service.add_member(community.id, user2.id, "member")

        assert service.is_curator_or_owner(community.id, user2.id) is False

        result = service.update_member_role(community.id, user2.id, "curator")
        assert result is True

        assert service.is_curator_or_owner(community.id, user2.id) is True

        db.session.delete(community)
        db.session.delete(user2)
        db.session.commit()


def test_community_service_get_community_members(test_client):
    """Test getting community members via service"""
    with test_client.application.app_context():
        service = CommunityService()
        user = User.query.filter_by(email="test@example.com").first()

        user2 = User(email="svc-get-members@example.com", password="test1234")
        db.session.add(user2)
        db.session.commit()

        community = service.create_community(
            name="Get Members Service Test",
            slug="get-members-service-test",
            owner_id=user.id,
        )

        service.add_member(community.id, user2.id, "member")

        members = service.get_community_members(community.id)
        assert len(members) == 2

        db.session.delete(community)
        db.session.delete(user2)
        db.session.commit()


def test_community_service_get_user_communities(test_client):
    """Test getting user's communities via service"""
    with test_client.application.app_context():
        service = CommunityService()
        user = User.query.filter_by(email="test@example.com").first()

        community = service.create_community(
            name="User Communities Test",
            slug="user-communities-test",
            owner_id=user.id,
        )

        communities = service.get_user_communities(user.id)
        assert len(communities) >= 1
        assert any(c.id == community.id for c in communities)

        db.session.delete(community)
        db.session.commit()
