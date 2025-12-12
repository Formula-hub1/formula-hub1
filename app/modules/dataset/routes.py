import json
import logging
import os
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from zipfile import ZipFile

from flask import abort, jsonify, make_response, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required

from app.modules.auth.services import AuthenticationService
from app.modules.dataset import dataset_bp
from app.modules.dataset.forms import FormulaDataSetForm, UVLDataSetForm
from app.modules.dataset.models import Comment, DSDownloadRecord
from app.modules.dataset.services import (
    AuthorService,
    CommentService,
    DataSetService,
    DOIMappingService,
    DSDownloadRecordService,
    DSMetaDataService,
    DSViewRecordService,
)
from app.modules.zenodo.services import ZenodoService

comment_service = CommentService()

logger = logging.getLogger(__name__)


dataset_service = DataSetService()
author_service = AuthorService()
dsmetadata_service = DSMetaDataService()
zenodo_service = ZenodoService()
doi_mapping_service = DOIMappingService()
ds_view_record_service = DSViewRecordService()


@dataset_bp.route("/dataset/upload", methods=["GET", "POST"])
@login_required
def create_dataset():
    # 2. LÓGICA PARA GESTIONAR AMBOS FORMULARIOS
    uvl_form = UVLDataSetForm()
    formula_form = FormulaDataSetForm()

    if request.method == "POST":
        dataset = None
        form_to_process = None

        # Determinar cuál formulario se ha enviado validándolos
        if uvl_form.validate_on_submit():
            form_to_process = uvl_form
        elif formula_form.validate_on_submit():
            form_to_process = formula_form

        if form_to_process:
            try:
                logger.info(f"Creating dataset using {type(form_to_process).__name__}...")

                # El servicio ya sabe cómo manejar cada tipo (modificamos services.py antes)
                dataset = dataset_service.create_from_form(form=form_to_process, current_user=current_user)
                logger.info(f"Created dataset: {dataset}")

                # Mover archivos solo si es UVL (Formula CSV ya se procesó en memoria)
                if isinstance(form_to_process, UVLDataSetForm):
                    dataset_service.move_feature_models(dataset)

                # --- CÁLCULO DE RECOMENDACIONES ---
                try:
                    dataset_service.save_dataset_recommendations(dataset)
                except Exception as e:
                    logger.exception(f"Exception while calculating recommendations locally: {e}")

                # --- ZENODO ---
                data = {}
                try:
                    zenodo_response_json = zenodo_service.create_new_deposition(dataset)
                    response_data = json.dumps(zenodo_response_json)
                    data = json.loads(response_data)
                except Exception as exc:
                    fake_doi = f"10.1234/local-dataset-{dataset.id}"
                    dataset_service.update_dsmetadata(dataset.ds_meta_data_id, dataset_doi=fake_doi)
                    # ------------------

                    data = {}
                    logger.exception(f"Exception while create dataset data in Zenodo: {exc}")

                if data.get("conceptrecid"):
                    deposition_id = data.get("id")
                    dataset_service.update_dsmetadata(dataset.ds_meta_data_id, deposition_id=deposition_id)

                    try:
                        # Subir archivos a Zenodo (Solo UVL por ahora)
                        if isinstance(form_to_process, UVLDataSetForm):
                            for feature_model in dataset.feature_models:
                                zenodo_service.upload_file(dataset, deposition_id, feature_model)

                        zenodo_service.publish_deposition(deposition_id)
                        deposition_doi = zenodo_service.get_doi(deposition_id)
                        dataset_service.update_dsmetadata(dataset.ds_meta_data_id, dataset_doi=deposition_doi)
                    except Exception as e:
                        msg = f"Zenodo upload error: {e}"
                        return jsonify({"message": msg}), 200

                # Borrar temporales
                file_path = current_user.temp_folder()
                if os.path.exists(file_path) and os.path.isdir(file_path):
                    shutil.rmtree(file_path)

                msg = "Everything works!"
                return jsonify({"message": msg}), 200

            except Exception as exc:
                logger.exception(f"Exception while create dataset data in local {exc}")
                return jsonify({"Exception while create dataset data in local: ": str(exc)}), 400

        else:
            # Si ninguno validó, devolver errores combinados
            errors = uvl_form.errors if uvl_form.errors else formula_form.errors
            return jsonify({"message": errors}), 400

    # Pasar ambos formularios al template
    return render_template("dataset/upload_dataset.html", form=uvl_form, formula_form=formula_form)


@dataset_bp.route("/dataset/list", methods=["GET", "POST"])
@login_required
def list_dataset():
    return render_template(
        "dataset/list_datasets.html",
        datasets=dataset_service.get_synchronized(current_user.id),
        local_datasets=dataset_service.get_unsynchronized(current_user.id),
    )


@dataset_bp.route("/dataset/file/upload", methods=["POST"])
@login_required
def upload():
    file = request.files["file"]
    temp_folder = current_user.temp_folder()

    if not file or not (file.filename.endswith(".uvl") or file.filename.endswith(".csv")):
        return jsonify({"message": "No valid file. Only .uvl or .csv allowed"}), 400

    # create temp folder
    if not os.path.exists(temp_folder):
        os.makedirs(temp_folder)

    file_path = os.path.join(temp_folder, file.filename)

    if os.path.exists(file_path):
        # Generate unique filename (by recursion)
        base_name, extension = os.path.splitext(file.filename)
        i = 1
        while os.path.exists(os.path.join(temp_folder, f"{base_name} ({i}){extension}")):
            i += 1
        new_filename = f"{base_name} ({i}){extension}"
        file_path = os.path.join(temp_folder, new_filename)
    else:
        new_filename = file.filename

    try:
        file.save(file_path)
    except Exception as e:
        return jsonify({"message": str(e)}), 500

    return (
        jsonify(
            {
                "message": "UVL uploaded and validated successfully",
                "filename": new_filename,
            }
        ),
        200,
    )


@dataset_bp.route("/dataset/file/delete", methods=["POST"])
def delete():
    data = request.get_json()
    filename = data.get("file")
    temp_folder = current_user.temp_folder()
    filepath = os.path.join(temp_folder, filename)

    if os.path.exists(filepath):
        os.remove(filepath)
        return jsonify({"message": "File deleted successfully"})

    return jsonify({"error": "Error: File not found"})


@dataset_bp.route("/dataset/download/<int:dataset_id>", methods=["GET"])
def download_dataset(dataset_id):
    dataset = dataset_service.get_or_404(dataset_id)

    file_path = f"uploads/user_{dataset.user_id}/dataset_{dataset.id}/"

    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, f"dataset_{dataset_id}.zip")

    with ZipFile(zip_path, "w") as zipf:
        for subdir, dirs, files in os.walk(file_path):
            for file in files:
                full_path = os.path.join(subdir, file)

                relative_path = os.path.relpath(full_path, file_path)

                zipf.write(
                    full_path,
                    arcname=os.path.join(os.path.basename(zip_path[:-4]), relative_path),
                )

    user_cookie = request.cookies.get("download_cookie")
    if not user_cookie:
        user_cookie = str(uuid.uuid4())  # Generate a new unique identifier if it does not exist
        # Save the cookie to the user's browser
        resp = make_response(
            send_from_directory(
                temp_dir,
                f"dataset_{dataset_id}.zip",
                as_attachment=True,
                mimetype="application/zip",
            )
        )
        resp.set_cookie("download_cookie", user_cookie)
    else:
        resp = send_from_directory(
            temp_dir,
            f"dataset_{dataset_id}.zip",
            as_attachment=True,
            mimetype="application/zip",
        )

    # Check if the download record already exists for this cookie
    existing_record = DSDownloadRecord.query.filter_by(
        user_id=current_user.id if current_user.is_authenticated else None,
        dataset_id=dataset_id,
        download_cookie=user_cookie,
    ).first()

    if not existing_record:
        # Record the download in your database
        DSDownloadRecordService().create(
            user_id=current_user.id if current_user.is_authenticated else None,
            dataset_id=dataset_id,
            download_date=datetime.now(timezone.utc),
            download_cookie=user_cookie,
        )

    return resp


@dataset_bp.route("/doi/<path:doi>/", methods=["GET"], strict_slashes=False)
@dataset_bp.route("/doi/<path:doi>", methods=["GET"], strict_slashes=False)
def subdomain_index(doi):
    print(f"El DOI recibido es: '{doi}'")
    # Check if the DOI is an old DOI
    new_doi = doi_mapping_service.get_new_doi(doi)
    if new_doi:
        # Redirect to the same path with the new DOI
        return redirect(url_for("dataset.subdomain_index", doi=new_doi), code=302)

    # Try to search the dataset by the provided DOI (which should already be the new one)
    ds_meta_data = dsmetadata_service.filter_by_doi(doi)

    if not ds_meta_data:
        abort(404)

    # Get dataset
    dataset = ds_meta_data.dataset

    if dataset is None:
        abort(404)

    # Save the cookie to the user's browser
    user_cookie = ds_view_record_service.create_cookie(dataset=dataset)
    resp = make_response(render_template("dataset/view_dataset.html", dataset=dataset))
    resp.set_cookie("view_cookie", user_cookie)

    return resp


@dataset_bp.route("/dataset/unsynchronized/<int:dataset_id>/", methods=["GET"])
@login_required
def get_unsynchronized_dataset(dataset_id):

    # Get dataset
    dataset = dataset_service.get_unsynchronized_dataset(current_user.id, dataset_id)

    if not dataset:
        abort(404)

    return render_template("dataset/view_dataset.html", dataset=dataset)


@dataset_bp.route("/datasets/<int:dataset_id>/recommendations", methods=["GET"])
def get_recommendations_api(dataset_id):
    try:
        dataset = dataset_service.get_by_id(dataset_id)
    except Exception as exc:
        logger.error(f"Error retrieving dataset {dataset_id}: {exc}")
        return jsonify({"error": "Dataset not found"}), 404

    if not dataset:
        return jsonify({"error": "Dataset not found"}), 404

    try:
        json_data = dataset_service.get_or_recalculate_recommendations(dataset)

        if json_data:
            recommended_datasets = json.loads(json_data)
        else:
            recommended_datasets = []

        return jsonify({"dataset_id": dataset_id, "recommended_datasets": recommended_datasets}), 200

    except Exception as exc:
        logger.error(f"Error processing recommendation data for DS {dataset_id}: {exc}")
        return jsonify({"error": "Internal error processing recommendation data."}), 500


@dataset_bp.route("/datasets/<int:dataset_id>/comments", methods=["POST"])
@login_required
def add_comment(dataset_id):
    content = request.form.get("content")
    if not content or content.strip() == "":
        abort(400, description="El contenido del comentario no puede estar vacío.")
    parent_id = request.form.get("parent_id") or None
    auth_service = AuthenticationService()
    user = auth_service.get_authenticated_user()
    dataset = dataset_service.get_or_404(dataset_id)
    comment_service.create(content=content, dataset_id=dataset_id, parent_id=parent_id, user_id=user.id)
    return redirect(f"/doi/{dataset.ds_meta_data.dataset_doi}")


@dataset_bp.route("/datasets/<int:dataset_id>/comments/fragment", methods=["GET"])
def comments_fragment(dataset_id):
    """Devuelve el HTML de los comentarios (sin reply) para el modal"""
    comments = Comment.query.filter_by(dataset_id=dataset_id, parent_id=None).all()
    return render_template("dataset/comments_list.html", comments=comments)


@dataset_bp.route("/datasets/<int:dataset_id>/comments/ajax", methods=["POST"])
@login_required
def add_comment_ajax(dataset_id):
    """Crea un comentario desde el modal y devuelve la lista actualizada"""
    content = (request.form.get("content") or "").strip()
    if not content:
        return jsonify({"ok": False, "error": "El contenido no puede estar vacío."}), 400

    user = AuthenticationService().get_authenticated_user()
    comment_service.create(content=content, dataset_id=dataset_id, user_id=user.id)

    comments = Comment.query.filter_by(dataset_id=dataset_id, parent_id=None).all()
    html = render_template("dataset/comments_list.html", comments=comments)
    return jsonify({"ok": True, "html": html})
