from locust import HttpUser, TaskSet, events, task

from app import create_app
from app.modules.auth.repositories import UserRepository
from app.modules.auth.services import AuthenticationService
from core.environment.host import get_host_for_locust_testing
from core.locust.common import fake, get_csrf_token


class SignupBehavior(TaskSet):
    def on_start(self):
        self.signup()

    @task
    def signup(self):
        response = self.client.get("/signup")
        csrf_token = get_csrf_token(response)

        response = self.client.post(
            "/signup", data={"email": fake.email(), "password": fake.password(), "csrf_token": csrf_token}
        )
        if response.status_code != 200:
            print(f"Signup failed: {response.status_code}")


class LoginBehavior(TaskSet):
    def on_start(self):
        self.ensure_logged_out()
        self.login()

    @task
    def ensure_logged_out(self):
        response = self.client.get("/logout")
        if response.status_code != 200:
            print(f"Logout failed or no active session: {response.status_code}")

    @task
    def login(self):
        response = self.client.get("/login")
        if response.status_code != 200 or "Login" not in response.text:
            print("Already logged in or unexpected response, redirecting to logout")
            self.ensure_logged_out()
            response = self.client.get("/login")

        csrf_token = get_csrf_token(response)

        response = self.client.post(
            "/login", data={"email": "user1@example.com", "password": "1234", "csrf_token": csrf_token}
        )
        if response.status_code != 200:
            print(f"Login failed: {response.status_code}")


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    global VALID_RESET_TOKEN

    app = create_app("development")

    with app.app_context():
        try:
            auth_service = AuthenticationService()
            user_repo = UserRepository()

            user = user_repo.get_by_email(RESET_TEST_EMAIL)
            if not user:
                user = auth_service.create_with_profile(
                    name="Locust Single", surname="User", email=RESET_TEST_EMAIL, password=INITIAL_PASSWORD
                )

            token = auth_service.generate_reset_token(user.id)

            VALID_RESET_TOKEN = token

        except Exception as e:
            print(f"ERROR FATAL en la inicialización de Locust (no se pudo crear DB/token): {e}")
            VALID_RESET_TOKEN = "MOCK_FAIL_TOKEN"


RESET_TEST_EMAIL = "user1@example.com"
INITIAL_PASSWORD = "1234"
NEW_PASSWORD = "newsecurepassword456"
VALID_RESET_TOKEN = None


class PasswordResetBehavior(TaskSet):

    def on_start(self):
        self.email = RESET_TEST_EMAIL

    @task(1)
    def request_recovery_email(self):

        response = self.client.get("/recover-password/")
        csrf_token = get_csrf_token(response)

        response = self.client.post(
            "/recover-password/", data={"email": self.email, "csrf_token": csrf_token}, name="/recover-password/ [POST]"
        )

        if response.status_code == 200:
            pass
        else:
            print(f"Request recovery failed: {response.status_code}")

    @task(3)
    def navigate_away(self):
        self.client.get("/")

    @task(1)
    def reset_password_flow(self):
        token = VALID_RESET_TOKEN

        if token is None or token == "MOCK_FAIL_TOKEN":
            self.environment.stats.log_failure("PasswordResetBehavior", "Token not generated")
            return

        response = self.client.get(f"/reset-password/?token={token}")
        csrf_token = get_csrf_token(response)

        response = self.client.post(
            f"/reset-password/?token={token}",
            data={"password": NEW_PASSWORD, "new_password": NEW_PASSWORD, "csrf_token": csrf_token},
            name="/reset-password/ [POST]",
        )

        if response.status_code == 302:
            self.client.get("/login")
        elif response.status_code != 200:
            print(f"Password reset failed: {response.status_code}")


class AuthUser(HttpUser):
    tasks = {SignupBehavior: 5, LoginBehavior: 5, PasswordResetBehavior: 1}
    min_wait = 5000
    max_wait = 9000
    host = get_host_for_locust_testing()
