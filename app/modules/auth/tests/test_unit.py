import pytest
from flask import url_for

from app.modules.auth.repositories import UserRepository
from app.modules.auth.services import AuthenticationService
from app.modules.profile.repositories import UserProfileRepository


@pytest.fixture(scope="module")
def test_client(test_client):
    """
    Extends the test_client fixture to add additional specific data for module testing.
    """
    with test_client.application.app_context():
        # Add HERE new elements to the database that you want to exist in the test context.
        # DO NOT FORGET to use db.session.add(<element>) and db.session.commit() to save the data.
        pass

    yield test_client


def test_login_success(test_client):
    response = test_client.post(
        "/login", data=dict(email="test@example.com", password="test1234"), follow_redirects=True
    )

    assert response.request.path != url_for("auth.login"), "Login was unsuccessful"

    test_client.get("/logout", follow_redirects=True)


def test_login_unsuccessful_bad_email(test_client):
    response = test_client.post(
        "/login", data=dict(email="bademail@example.com", password="test1234"), follow_redirects=True
    )

    assert response.request.path == url_for("auth.login"), "Login was unsuccessful"

    test_client.get("/logout", follow_redirects=True)


def test_login_unsuccessful_bad_password(test_client):
    response = test_client.post(
        "/login", data=dict(email="test@example.com", password="basspassword"), follow_redirects=True
    )

    assert response.request.path == url_for("auth.login"), "Login was unsuccessful"

    test_client.get("/logout", follow_redirects=True)


def test_signup_user_no_name(test_client):
    response = test_client.post(
        "/signup", data=dict(surname="Foo", email="test@example.com", password="test1234"), follow_redirects=True
    )
    assert response.request.path == url_for("auth.show_signup_form"), "Signup was unsuccessful"
    assert b"This field is required" in response.data, response.data


def test_signup_user_unsuccessful(test_client):
    email = "test@example.com"
    response = test_client.post(
        "/signup", data=dict(name="Test", surname="Foo", email=email, password="test1234"), follow_redirects=True
    )
    assert response.request.path == url_for("auth.show_signup_form"), "Signup was unsuccessful"
    assert f"Email {email} in use".encode("utf-8") in response.data


def test_signup_user_successful(test_client):
    response = test_client.post(
        "/signup",
        data=dict(name="Foo", surname="Example", email="foo@example.com", password="foo1234"),
        follow_redirects=True,
    )
    assert response.request.path == url_for("public.index"), "Signup was unsuccessful"


def test_service_create_with_profie_success(clean_database):
    data = {"name": "Test", "surname": "Foo", "email": "service_test@example.com", "password": "test1234"}

    AuthenticationService().create_with_profile(**data)

    assert UserRepository().count() == 1
    assert UserProfileRepository().count() == 1


def test_service_create_with_profile_fail_no_email(clean_database):
    data = {"name": "Test", "surname": "Foo", "email": "", "password": "1234"}

    with pytest.raises(ValueError, match="Email is required."):
        AuthenticationService().create_with_profile(**data)

    assert UserRepository().count() == 0
    assert UserProfileRepository().count() == 0


def test_service_create_with_profile_fail_no_password(clean_database):
    data = {"name": "Test", "surname": "Foo", "email": "test@example.com", "password": ""}

    with pytest.raises(ValueError, match="Password is required."):
        AuthenticationService().create_with_profile(**data)

    assert UserRepository().count() == 0
    assert UserProfileRepository().count() == 0


# Recover password test


def test_service_recover_password_email_success(clean_database, mocker):
    data = {"name": "Test", "surname": "Recover", "email": "recover@example.com", "password": "test1234"}
    user = AuthenticationService().create_with_profile(**data)

    mocker.patch("app.modules.auth.services.mail.send")

    result = AuthenticationService().send_email(email="recover@example.com")

    assert "Email succesfully sent to recover@example.com" in result


def test_service_recover_password_email_fail_no_user(clean_database, mocker):
    mocker.patch("app.modules.auth.services.mail.send")

    email = "nonexistent@example.com"
    result = AuthenticationService().send_email(email=email)

    assert "Email should be associated to an existing account" in result
    assert mocker.patch("app.modules.auth.services.mail.send").call_count == 0, "mail.send should not have been called"


def test_recover_password_form_fail_no_email(test_client):
    response = test_client.post("/recover-password/", data=dict(email=""), follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"] == "/"


def test_recover_password_form_fail_nonexistent_email(test_client, mocker):
    email = "nonexistent@example.com"
    mocker.patch(
        "app.modules.auth.services.AuthenticationService.send_email",
        return_value="Email should be associated to an existing account",
    )

    mocker.patch("app.modules.auth.services.AuthenticationService.is_email_available", return_value=True)

    response = test_client.post("/recover-password/", data=dict(email=email), follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"] == "/"


def test_reset_password_form_success(test_client, clean_database):
    data = {"name": "Test", "surname": "Reset", "email": "reset@example.com", "password": "oldpassword"}
    user = AuthenticationService().create_with_profile(**data)
    user_id = user.id

    token = AuthenticationService().generate_reset_token(user_id)
    new_password = "newpassword1234"

    response = test_client.post(
        f"/reset-password/?token={token}",
        data=dict(password=new_password, new_password=new_password),
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"] == url_for("auth.login", _external=False)

    updated_user = UserRepository().get_by_id(user_id)
    assert updated_user.check_password(new_password)


def test_reset_password_form_fail_invalid_token(test_client):
    invalid_token = "invalid.token.12345"

    response = test_client.get(f"/reset-password/?token={invalid_token}", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"] == url_for("auth.login", _external=False)


def test_reset_password_form_fail_same_password(test_client, clean_database):
    old_password = "sameoldpassword"
    data = {"name": "Test", "surname": "Same", "email": "same@example.com", "password": old_password}
    user = AuthenticationService().create_with_profile(**data)
    user_id = user.id

    token = AuthenticationService().generate_reset_token(user_id)

    response = test_client.post(
        f"/reset-password/?token={token}",
        data=dict(password=old_password, new_password=old_password),
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert b"New password can not be the same as the last one." in response.data
