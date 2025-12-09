import os
import subprocess
from datetime import datetime, timezone

from flask import abort

import docker
from app.modules.webhook.repositories import WebhookRepository
from core.services.BaseService import BaseService

FLASK_ENV = os.getenv("FLASK_ENV", "production")

if FLASK_ENV in ["development", "testing"]:
    # Esto es seguro en local (docker compose), pero peligroso en la nube.
    # Solo se debe ejecutar si el contenedor tiene acceso al socket (que no es el caso de Render).
    try:
        client = docker.from_env()
    except Exception as e:
        # En caso de error, inicializamos a None para evitar que el worker falle
        print(f"⚠️ Docker client initialization failed (Expected in Render): {e}")
        client = None
else:
    # En producción (Render), el cliente Docker debe ser None para evitar el crash.
    client = None


class WebhookService(BaseService):
    def __init__(self):
        super().__init__(WebhookRepository())

    def get_web_container(self):
        try:
            return client.containers.get("web_app_container")
        except docker.errors.NotFound:
            abort(404, description="Web container not found.")

    def get_volume_name(self, container):
        volume_name = next(
            (
                mount.get("Name") or mount.get("Source")
                for mount in container.attrs["Mounts"]
                if mount["Destination"] == "/app"
            ),
            None,
        )

        if not volume_name:
            raise ValueError("No volume or bind mount found mounted on /app")

        return volume_name

    def execute_host_command(self, volume_name, command):
        try:
            subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-v",
                    f"{volume_name}:/app",
                    "-v",
                    "/var/run/docker.sock:/var/run/docker.sock",
                    "-w",
                    "/app",
                    *command,
                ],
                check=True,
            )
        except subprocess.CalledProcessError as e:
            abort(500, description=f"Host command failed: {str(e)}")

    def execute_container_command(self, container, command, workdir="/app"):
        exit_code, output = container.exec_run(command, workdir=workdir)
        if exit_code != 0:
            abort(500, description=f"Container command failed: {output.decode('utf-8')}")
        return output.decode("utf-8")

    def log_deployment(self, container):
        log_entry = f"Deployment successful at {datetime.now(timezone.utc).isoformat()}\n"
        log_file_path = "/app/deployments.log"
        self.execute_container_command(container, f"sh -c 'echo \"{log_entry}\" >> {log_file_path}'")

    def restart_container(self, container):
        subprocess.Popen(["/bin/sh", "/app/scripts/restart_container.sh", container.id])
