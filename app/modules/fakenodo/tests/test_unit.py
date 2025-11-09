import pytest
from app import create_app

@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

def test_connection_fakenodo(client):
    response = client.get("/fakenodo/api")
    data = response.get_json()
    assert response.status_code == 200
    assert data["status"] == "success"
    assert data["message"] == "FakeNodo API is working."

def test_create_fakenodo(client):
    response = client.post("/fakenodo/api")
    data = response.get_json()
    assert response.status_code == 201
    assert data["status"] == "success"
    assert data["message"] == "FakeNodo created successfully!"

def test_deposition_files_fakenodo(client):
    deposition_id = "test_deposition"
    response = client.post(f"/fakenodo/api/{deposition_id}/files")
    data = response.get_json()
    assert response.status_code == 201
    assert data["status"] == "success"
    assert data["message"] == f"Created deposition {deposition_id} successfully!"

def test_delete_deposition_fakenodo(client):
    deposition_id = "test_deposition"
    response = client.delete(f"/fakenodo/api/{deposition_id}")
    data = response.get_json()
    assert response.status_code == 200
    assert data["status"] == "success"
    assert data["message"] == f"Deleted deposition {deposition_id} successfully!"

def test_publish_deposition_fakenodo(client):
    deposition_id = "test_deposition"
    response = client.post(f"/fakenodo/api/{deposition_id}/actions/publish")
    data = response.get_json()
    assert response.status_code == 202
    assert data["status"] == "success"
    assert data["message"] == f"Published deposition {deposition_id} successfully!" 

def test_get_deposition_fakenodo(client):
    deposition_id = "test_deposition"
    response = client.get(f"/fakenodo/api/{deposition_id}")
    data = response.get_json()
    assert response.status_code == 200
    assert data["status"] == "success"
    assert data["message"] == f"Fetched deposition {deposition_id} successfully!"
    assert data["doi"] == "10.1234/fakenodo.123456"