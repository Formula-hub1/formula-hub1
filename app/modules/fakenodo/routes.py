from flask import jsonify, make_response, request
import uuid
from datetime import datetime

from app.modules.fakenodo import fakenodo_bp

base_url = "/fakenodo/api"

FAKE_ZENODO_RECORDS = {}


def generate_fake_doi(record_id, version):
    return f"10.1234/fakenodo.{record_id[:6]}v{version}"


@fakenodo_bp.route(base_url, methods=["GET"])
def test_fakenodo():
    response = {
        "status": "success",
        "message": "FakeNodo API is working.",
    }
    return jsonify(response)


@fakenodo_bp.route(base_url, methods=["POST"])
def create_fakenodo():
    depositionId = str(uuid.uuid4())
    record_id = depositionId
    FAKE_ZENODO_RECORDS[depositionId] = {
        "record_id": record_id,
        "version": 1,
        "doi": None,
        "metadata_updated": False,
        "files_updated": False,
        "published": False,
        "created": datetime.now().isoformat(),
        "latest_version": depositionId
    }
    if request.get_json(silent=True):
        FAKE_ZENODO_RECORDS[depositionId]["metadata_updated"] = True
    response = {
        "status": "success",
        "message": "FakeNodo created successfully!",
        "id": depositionId,
        "links": {
            "self": f"http://localhost/fakenodo/api/{depositionId}"
        }
    }
    return make_response(jsonify(response), 201)


@fakenodo_bp.route(base_url + "/<depositionId>/files", methods=["POST"])
def deposition_files_fakenodo(depositionId):
    if depositionId not in FAKE_ZENODO_RECORDS:
        return make_response(jsonify({"message": "Deposition not found"}), 404)
    FAKE_ZENODO_RECORDS[depositionId]["files_updated"] = True
    response = {
        "status": "success",
        "message": f"Created deposition {depositionId} successfully!",
    }
    return make_response(jsonify(response), 201)


@fakenodo_bp.route(base_url + "/<depositionId>", methods=["DELETE"])
def delete_deposition_fakenodo(depositionId):
    if depositionId in FAKE_ZENODO_RECORDS:
        del FAKE_ZENODO_RECORDS[depositionId]
        message = f"Deleted deposition {depositionId} successfully!"
        status_code = 200
    else:
        message = f"Deposition {depositionId} not found."
        status_code = 404
    response = {
        "status": "success",
        "message": message,
    }
    return make_response(jsonify(response), status_code)


@fakenodo_bp.route(base_url + "/<depositionId>/actions/publish", methods=["POST"])
def publish_deposition_fakenodo(depositionId):
    if depositionId not in FAKE_ZENODO_RECORDS:
        return make_response(jsonify({"message": "Deposition not found"}), 404)
    record = FAKE_ZENODO_RECORDS[depositionId]
    if record["metadata_updated"] and not record["files_updated"]:
        if record["published"]:
            doi = record["doi"]
            version = record["version"]
        else:
            version = 1
            doi = generate_fake_doi(record["record_id"], version)
    elif record["files_updated"]:
        version = record["version"] + 1
        doi = generate_fake_doi(record["record_id"], version)
        record["version"] = version
        record["doi"] = doi
        record["files_updated"] = False
        record["metadata_updated"] = False
    else:
        version = record.get("version", 1)
        doi = record.get("doi") or generate_fake_doi(record["record_id"], version)
    record["published"] = True
    record["doi"] = doi
    record["version"] = version
    response = {
        "status": "success",
        "message": f"Published deposition {depositionId} successfully!",
        "doi": doi,
        "version": version,
    }
    return make_response(jsonify(response), 202)


@fakenodo_bp.route(base_url + "/<depositionId>", methods=["GET"])
def get_deposition_fakenodo(depositionId):
    if depositionId not in FAKE_ZENODO_RECORDS:
        return make_response(jsonify({"message": "Deposition not found"}), 404)
    record = FAKE_ZENODO_RECORDS[depositionId]
    response = {
        "status": "success",
        "message": f"Fetched deposition {depositionId} successfully!",
        "doi": record.get("doi", "N/A - Not yet published"),
        "version": record.get("version", 1),
        "published": record["published"],
        "versions": [
            {
                "id": dep_id,
                "version": data["version"],
                "doi": data.get("doi", "N/A"),
            }
            for dep_id, data in FAKE_ZENODO_RECORDS.items()
            if data["record_id"] == record["record_id"] and data["published"]
        ]
    }
    return make_response(jsonify(response), 200)
