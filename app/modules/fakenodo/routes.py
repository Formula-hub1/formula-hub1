from flask import render_template, jsonify, make_response
from app.modules.fakenodo import fakenodo_bp

base_url = "/fakenodo/api"

@fakenodo_bp.route(base_url, methods=['GET'])
def test_fakenodo():
    response = {
        "status": "success",
        "message": "FakeNododo API is working!",
    }
    return jsonify(response)

@fakenodo_bp.route(base_url, methods=['POST'])
def create_fakenodo():
    response = {
        "status": "success",
        "message": "FakeNododo created successfully!",
    }
    return make_response(jsonify(response), 201)

@fakenodo_bp.route(base_url + '/<depositionId>/files', methods=['POST'])
def deposition_files_fakenodo(depositionId):
    response = {
        "status": "success",
        "message": f"Created deposition {depositionId} successfully!",
    }
    return make_response(jsonify(response), 201)

@fakenodo_bp.route(base_url + '/<depositionId>', methods=['DELETE'])
def delete_deposition_fakenodo(depositionId):
    response = {
        "status": "success",
        "message": f"Deleted deposition {depositionId} successfully!",
    }
    return make_response(jsonify(response), 200)

@fakenodo_bp.route(base_url + '/<depositionId>/actions/publish', methods=['POST'])
def publish_deposition_fakenodo(depositionId):
    response = {
        "status": "success",
        "message": f"Published deposition {depositionId} successfully!",
    }
    return make_response(jsonify(response), 202)

@fakenodo_bp.route(base_url + '/<depositionId>', methods=['GET'])
def get_deposition_fakenodo(depositionId):
    response = {
        "status": "success",
        "message": f"Fetched deposition {depositionId} successfully!",
        "doi": "10.1234/fakenodo.123456",
    }
    return make_response(jsonify(response), 200)
