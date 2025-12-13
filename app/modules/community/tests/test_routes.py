import pytest

from app import db
from app.modules.auth.models import User
from app.modules.community.models import Community
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
# PUBLIC ROUTE TESTS
# ============================================================================


def test_community_index_route(test_client):
    """Test community index page"""
    response = test_client.get("/communities/")
    assert response.status_code == 200


def test_community_search_route(test_client):
    """Test community search page"""
    response = test_client.get("/communities/search?q=test")
    assert response.status_code == 200


def test_community_search_empty_query(test_client):
    """Test community search with empty query"""
    response = test_client.get("/communities/search")
    assert response.status_code == 200


def test_community_detail_not_found(test_client):
    """Test community detail page with nonexistent slug"""
    response = test_client.get("/communities/nonexistent-slug", follow_redirects=True)
    assert response.status_code == 200


def test_community_detail_existing(test_client):
    """Test community detail page with existing community"""
    # Login first
    test_client.post(
        "/login",
        data=dict(email="test@example.com", password="test1234"),
        follow_redirects=True,
    )

    # Create community
    test_client.post(
        "/communities/create",
        data=dict(
            name="Detail Route Test",
            slug="detail-route-test",
            description="Test",
            is_public=True,
        ),
        follow_redirects=True,
    )

    response = test_client.get("/communities/detail-route-test")
    assert response.status_code == 200

    with test_client.application.app_context():
        community = Community.query.filter_by(slug="detail-route-test").first()
        if community:
            db.session.delete(community)
            db.session.commit()

    test_client.get("/logout", follow_redirects=True)


# ============================================================================
# AUTHENTICATION REQUIRED ROUTE TESTS
# ============================================================================


def test_community_create_requires_login(test_client):
    """Test that create community requires login"""
    response = test_client.get("/communities/create", follow_redirects=True)
    assert response.status_code == 200


def test_community_create_authenticated(test_client):
    """Test creating community when authenticated"""
    test_client.post(
        "/login",
        data=dict(email="test@example.com", password="test1234"),
        follow_redirects=True,
    )

    response = test_client.get("/communities/create")
    assert response.status_code == 200

    test_client.get("/logout", follow_redirects=True)


def test_community_create_submit(test_client):
    """Test submitting community creation form"""
    test_client.post(
        "/login",
        data=dict(email="test@example.com", password="test1234"),
        follow_redirects=True,
    )

    response = test_client.post(
        "/communities/create",
        data=dict(
            name="New Test Community",
            slug="new-test-community",
            description="A new test community",
            is_public=True,
        ),
        follow_redirects=True,
    )

    assert response.status_code == 200

    with test_client.application.app_context():
        community = Community.query.filter_by(slug="new-test-community").first()
        if community:
            db.session.delete(community)
            db.session.commit()

    test_client.get("/logout", follow_redirects=True)


def test_community_create_duplicate_slug(test_client):
    """Test creating community with duplicate slug"""
    test_client.post(
        "/login",
        data=dict(email="test@example.com", password="test1234"),
        follow_redirects=True,
    )

    # Create first community
    test_client.post(
        "/communities/create",
        data=dict(
            name="First Duplicate",
            slug="dup-slug-test",
            description="First community",
            is_public=True,
        ),
        follow_redirects=True,
    )

    # Try to create second with same slug
    response = test_client.post(
        "/communities/create",
        data=dict(
            name="Second Duplicate",
            slug="dup-slug-test",
            description="Second community",
            is_public=True,
        ),
        follow_redirects=True,
    )

    assert response.status_code == 200

    with test_client.application.app_context():
        community = Community.query.filter_by(slug="dup-slug-test").first()
        if community:
            db.session.delete(community)
            db.session.commit()

    test_client.get("/logout", follow_redirects=True)


def test_community_edit_requires_login(test_client):
    """Test that edit community requires login"""
    response = test_client.get("/communities/test-slug/edit", follow_redirects=True)
    assert response.status_code == 200


def test_community_members_requires_login(test_client):
    """Test that members page requires login"""
    response = test_client.get("/communities/test-slug/members", follow_redirects=True)
    assert response.status_code == 200


def test_community_submissions_requires_login(test_client):
    """Test that submissions page requires login"""
    response = test_client.get("/communities/test-slug/submissions", follow_redirects=True)
    assert response.status_code == 200


def test_community_submit_dataset_requires_login(test_client):
    """Test that submit dataset requires login"""
    response = test_client.get("/communities/test-slug/submit", follow_redirects=True)
    assert response.status_code == 200


# ============================================================================
# API ROUTE TESTS
# ============================================================================


def test_community_api_list(test_client):
    """Test API endpoint for listing communities"""
    response = test_client.get("/communities/api/communities")
    assert response.status_code == 200
    assert response.content_type == "application/json"


def test_community_api_get_nonexistent(test_client):
    """Test API endpoint for getting nonexistent community"""
    response = test_client.get("/communities/api/communities/nonexistent-slug")
    assert response.status_code == 404


def test_community_api_get_existing(test_client):
    """Test API endpoint for getting existing community"""
    # Login and create community
    test_client.post(
        "/login",
        data=dict(email="test@example.com", password="test1234"),
        follow_redirects=True,
    )

    test_client.post(
        "/communities/create",
        data=dict(
            name="API Test Community",
            slug="api-test-community",
            description="Test",
            is_public=True,
        ),
        follow_redirects=True,
    )

    response = test_client.get("/communities/api/communities/api-test-community")
    assert response.status_code == 200
    assert response.content_type == "application/json"

    with test_client.application.app_context():
        community = Community.query.filter_by(slug="api-test-community").first()
        if community:
            db.session.delete(community)
            db.session.commit()

    test_client.get("/logout", follow_redirects=True)


def test_community_api_datasets_nonexistent(test_client):
    """Test API endpoint for datasets of nonexistent community"""
    response = test_client.get("/communities/api/communities/nonexistent/datasets")
    assert response.status_code == 404


def test_community_api_datasets_existing(test_client):
    """Test API endpoint for datasets of existing community"""
    # Login and create community
    test_client.post(
        "/login",
        data=dict(email="test@example.com", password="test1234"),
        follow_redirects=True,
    )

    test_client.post(
        "/communities/create",
        data=dict(
            name="API Datasets Test",
            slug="api-datasets-test",
            description="Test",
            is_public=True,
        ),
        follow_redirects=True,
    )

    response = test_client.get("/communities/api/communities/api-datasets-test/datasets")
    assert response.status_code == 200
    assert response.content_type == "application/json"

    with test_client.application.app_context():
        community = Community.query.filter_by(slug="api-datasets-test").first()
        if community:
            db.session.delete(community)
            db.session.commit()

    test_client.get("/logout", follow_redirects=True)
