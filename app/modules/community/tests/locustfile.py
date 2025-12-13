from locust import HttpUser, TaskSet, task

from core.environment.host import get_host_for_locust_testing
from core.locust.common import fake, get_csrf_token


class CommunityBrowseBehavior(TaskSet):
    """Tasks for browsing communities"""

    @task(3)
    def list_communities(self):
        """Browse community list"""
        response = self.client.get("/communities/")
        if response.status_code != 200:
            print(f"List communities failed: {response.status_code}")

    @task(2)
    def search_communities(self):
        """Search for communities"""
        search_term = fake.word()
        response = self.client.get(f"/communities/search?q={search_term}")
        if response.status_code != 200:
            print(f"Search communities failed: {response.status_code}")

    @task(1)
    def api_list_communities(self):
        """Access community API"""
        response = self.client.get("/communities/api/communities")
        if response.status_code != 200:
            print(f"API list communities failed: {response.status_code}")


class CommunityAuthenticatedBehavior(TaskSet):
    """Tasks requiring authentication"""

    def on_start(self):
        """Login before performing authenticated tasks"""
        self.login()

    def login(self):
        """Perform login"""
        response = self.client.get("/login")
        if response.status_code != 200:
            print(f"Get login page failed: {response.status_code}")
            return

        csrf_token = get_csrf_token(response)

        response = self.client.post(
            "/login",
            data={
                "email": "user1@example.com",
                "password": "1234",
                "csrf_token": csrf_token,
            },
        )
        if response.status_code != 200:
            print(f"Login failed: {response.status_code}")

    @task(2)
    def view_create_page(self):
        """View community creation page"""
        response = self.client.get("/communities/create")
        if response.status_code != 200:
            print(f"View create page failed: {response.status_code}")

    @task(1)
    def create_community(self):
        """Create a new community"""
        response = self.client.get("/communities/create")
        if response.status_code != 200:
            print(f"Get create page failed: {response.status_code}")
            return

        csrf_token = get_csrf_token(response)
        unique_slug = f"locust-{fake.uuid4()[:8]}"

        response = self.client.post(
            "/communities/create",
            data={
                "name": f"Locust Test {fake.company()}",
                "slug": unique_slug,
                "description": fake.text(max_nb_chars=200),
                "is_public": True,
                "csrf_token": csrf_token,
            },
        )
        if response.status_code not in [200, 302]:
            print(f"Create community failed: {response.status_code}")

    @task(3)
    def browse_communities(self):
        """Browse community list while logged in"""
        response = self.client.get("/communities/")
        if response.status_code != 200:
            print(f"Browse communities failed: {response.status_code}")


class CommunityUser(HttpUser):
    """Locust user for community load testing"""

    tasks = [CommunityBrowseBehavior, CommunityAuthenticatedBehavior]
    min_wait = 5000
    max_wait = 9000
    host = get_host_for_locust_testing()
