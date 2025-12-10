import os

import itsdangerous
from flask import current_app, url_for
from flask_login import current_user, login_user
from flask_mail import Message

from app import mail
from app.modules.auth.models import User
from app.modules.auth.repositories import UserRepository
from app.modules.profile.models import UserProfile
from app.modules.profile.repositories import UserProfileRepository
from core.configuration.configuration import uploads_folder_name
from core.services.BaseService import BaseService


class AuthenticationService(BaseService):

    def __init__(self):
        self.user_repository = UserRepository()
        super().__init__(self.user_repository)
        self.user_profile_repository = UserProfileRepository()

    def _get_serializer(self):
        return itsdangerous.URLSafeTimedSerializer(current_app.config["SECRET_KEY"])

    def login(self, email, password, remember=True):
        user = self.repository.get_by_email(email)
        if user is not None and user.check_password(password):
            login_user(user, remember=remember)
            return True
        return False

    def is_email_available(self, email: str) -> bool:
        return self.repository.get_by_email(email) is None

    def create_with_profile(self, **kwargs):
        try:
            email = kwargs.pop("email", None)
            password = kwargs.pop("password", None)
            name = kwargs.pop("name", None)
            surname = kwargs.pop("surname", None)

            if not email:
                raise ValueError("Email is required.")
            if not password:
                raise ValueError("Password is required.")
            if not name:
                raise ValueError("Name is required.")
            if not surname:
                raise ValueError("Surname is required.")

            user_data = {"email": email, "password": password}

            profile_data = {
                "name": name,
                "surname": surname,
            }

            user = self.create(commit=False, **user_data)
            profile_data["user_id"] = user.id
            self.user_profile_repository.create(**profile_data)
            self.repository.session.commit()
        except Exception as exc:
            self.repository.session.rollback()
            raise exc
        return user

    def update_profile(self, user_profile_id, form):
        if form.validate():
            updated_instance = self.update(user_profile_id, **form.data)
            return updated_instance, None

        return None, form.errors

    def get_authenticated_user(self) -> User | None:
        if current_user.is_authenticated:
            return current_user
        return None

    def get_authenticated_user_profile(self) -> UserProfile | None:
        if current_user.is_authenticated:
            return current_user.profile
        return None

    def temp_folder_by_user(self, user: User) -> str:
        return os.path.join(uploads_folder_name(), "temp", str(user.id))

    def generate_reset_token(self, user_id):
        return self._get_serializer().dumps({"user_id": user_id})

    def verify_reset_token(self, token):
        try:
            data = self._get_serializer().loads(token, max_age=3600)
            user_id = data.get("user_id")

            if not data or not user_id:
                return None

            return self.user_repository.get_by_id(user_id)
        except (itsdangerous.SignatureExpired, itsdangerous.BadTimeSignature):
            return None
        except Exception as exc:
            print(f"Unexpected error during token verification: {exc}")
            return None

    def update_password(self, user_id, password):
        user = self.user_repository.get_by_id(user_id)
        if user:
            user.set_password(password)
            self.repository.session.commit()

    def send_email(self, **kwargs) -> str:
        email = kwargs.get("email")
        user = self.user_repository.get_by_email(email)
        if user is None:
            return "Email should be associated to an existing account"

        reset_token = self.generate_reset_token(user.id)
        recover_url = url_for("auth.reset_password_form", token=reset_token, _external=True)

        msg = Message(
            subject="Password recovery - Formula Hub",
            recipients=[email],
            body=(
                "Dear user\n\n"
                "There has been a request to reset your Formula Hub account password.\n\n"
                f"Reset your password clicking the following link: {recover_url}\n\n"
                "If you did not request a password reset, ignore this email."
            ),
        )

        mail.send(msg)

        return f"Email succesfully sent to {email}"
