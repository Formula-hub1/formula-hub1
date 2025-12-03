import io
import zipfile
from locust import HttpUser, TaskSet, task
from core.environment.host import get_host_for_locust_testing


class UploaderBehavior(TaskSet):
    """Comportamiento de usuario autenticado para el módulo uploader."""

    def on_start(self):
        """Se ejecuta al inicio. Realiza login y accede a la página."""
        self.login()
        self.index()

    def login(self):
        """Realiza login de usuario."""
        response = self.client.post("/login", data={
            "email": "user1@example.com",
            "password": "1234"
        })

        if response.status_code != 200:
            print(f"Login failed: {response.status_code}")

    def create_sample_zip(self, num_files=2):
        """Crea un ZIP de ejemplo con archivos .uvl."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            for i in range(num_files):
                uvl_content = f"""features
    Feature{i}
        mandatory
            SubFeature{i}

constraints
    Feature{i} => SubFeature{i}
"""
                zf.writestr(f"model_{i}.uvl", uvl_content)
        zip_buffer.seek(0)
        return zip_buffer

    @task(5)
    def index(self):
        """Tarea: Acceder a la página principal del uploader."""
        response = self.client.get("/uploader")

        if response.status_code != 200:
            print(f"Uploader index failed: {response.status_code}")

    @task(3)
    def upload_small_zip(self):
        """Tarea: Subir un ZIP pequeño con 2 archivos."""
        zip_file = self.create_sample_zip(num_files=2)

        response = self.client.post(
            "/uploader/preview",
            files={"file": ("test_small.zip", zip_file, "application/zip")}
        )

        if response.status_code != 200:
            print(f"Small ZIP upload failed: {response.status_code}")

    @task(2)
    def upload_medium_zip(self):
        """Tarea: Subir un ZIP mediano con 5 archivos."""
        zip_file = self.create_sample_zip(num_files=5)

        response = self.client.post(
            "/uploader/preview",
            files={"file": ("test_medium.zip", zip_file, "application/zip")}
        )

        if response.status_code != 200:
            print(f"Medium ZIP upload failed: {response.status_code}")

    @task(1)
    def upload_large_zip(self):
        """Tarea: Subir un ZIP grande con 10 archivos."""
        zip_file = self.create_sample_zip(num_files=10)

        response = self.client.post(
            "/uploader/preview",
            files={"file": ("test_large.zip", zip_file, "application/zip")}
        )

        if response.status_code != 200:
            print(f"Large ZIP upload failed: {response.status_code}")

    @task(2)
    def upload_github_url(self):
        """Tarea: Intentar subir desde URL de GitHub."""
        url = "https://github.com/diverso-lab/uvlhub/archive/"
        url += "refs/heads/main.zip"

        response = self.client.post(
            "/uploader/preview",
            data={"url": url}
        )

        if response.status_code not in [200, 400, 500]:
            print(f"GitHub URL upload failed: {response.status_code}")

    @task(1)
    def upload_invalid_file(self):
        """Tarea: Intentar subir archivo sin .uvl (test negativo)."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr("readme.txt", "This is not a UVL file")
        zip_buffer.seek(0)

        response = self.client.post(
            "/uploader/preview",
            files={"file": ("invalid.zip", zip_buffer, "application/zip")}
        )

        # Esperamos que falle (400 o redirección)
        if response.status_code == 200:
            status = response.status_code
            print(f"Invalid file should have failed but got: {status}")

    @task(1)
    def complete_upload_flow(self):
        """Tarea: Flujo completo de upload, preview y confirmación."""
        # Paso 1: Preview
        zip_file = self.create_sample_zip(num_files=2)

        preview_response = self.client.post(
            "/uploader/preview",
            files={"file": ("complete_flow.zip", zip_file,
                            "application/zip")}
        )

        if preview_response.status_code != 200:
            status = preview_response.status_code
            print(f"Preview in complete flow failed: {status}")
            return

        # Paso 2: Confirm
        confirm_data = {
            "dataset_title": "Load Test Dataset",
            "dataset_description": (
                "Dataset created during load testing with Locust"
            ),
            "dataset_publication_type": "OTHER",
            "dataset_tags": "test,loadtest,locust",
            "title_0": "Model 0",
            "description_0": "First model from load test",
            "title_1": "Model 1",
            "description_1": "Second model from load test"
        }

        confirm_response = self.client.post(
            "/uploader/confirm",
            data=confirm_data
        )

        if confirm_response.status_code != 200:
            print(f"Confirm failed: {confirm_response.status_code}")


class BulkUploaderBehavior(TaskSet):
    """Comportamiento para subidas masivas (stress test)."""

    def on_start(self):
        """Login y navegación inicial."""
        self.login()
        self.client.get("/uploader")

    def login(self):
        """Realiza login de usuario."""
        response = self.client.post("/login", data={
            "email": "test@uvlhub.io",
            "password": "test1234"
        })

        if response.status_code != 200:
            print(f"Login failed: {response.status_code}")

    @task
    def bulk_upload(self):
        """Tarea: Subir archivo con muchos modelos (20 archivos)."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            for i in range(20):
                uvl_content = f"""features
    BulkFeature{i}
        mandatory
            SubFeature{i}
            OptionalFeature{i}
                alternative
                    Option{i}A
                    Option{i}B

constraints
    BulkFeature{i} => SubFeature{i}
"""
                zf.writestr(f"bulk_model_{i}.uvl", uvl_content)

        zip_buffer.seek(0)

        response = self.client.post(
            "/uploader/preview",
            files={"file": ("bulk_upload.zip", zip_buffer, "application/zip")}
        )

        if response.status_code != 200:
            print(f"Bulk upload failed: {response.status_code}")


class UploaderUser(HttpUser):
    """Usuario autenticado que realiza operaciones normales de upload."""
    tasks = [UploaderBehavior]
    min_wait = 5000
    max_wait = 9000
    host = get_host_for_locust_testing()


class BulkUploaderUser(HttpUser):
    """Usuario que realiza subidas masivas (menor frecuencia)."""
    tasks = [BulkUploaderBehavior]
    min_wait = 10000
    max_wait = 15000
    host = get_host_for_locust_testing()
