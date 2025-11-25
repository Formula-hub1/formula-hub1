from app.modules.dataset.models import PublicationType
from flask import render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from app.modules.uploader.services import UploaderService
from app.modules.uploader import uploader_bp
import os
import base64

service = UploaderService()

@uploader_bp.route('/uploader', methods=['GET'])
def index():
    return render_template('uploader/index.html')

@uploader_bp.route("/uploader/preview", methods=["POST"])
@login_required
def preview_upload():
    file = request.files.get("file")
    github_url = request.form.get("url")

    if not file and not github_url:
        flash("No file or URL provided", "danger")
        return redirect(url_for("uploader.index"))

    try:
        preview_data = service.prepare_preview(file, github_url)
    except Exception as e:
        flash(str(e), "danger")
        return redirect(url_for("uploader.index"))

    temp_folder = os.path.join(service.base_upload_dir, f"user_{current_user.id}", "temp")
    os.makedirs(temp_folder, exist_ok=True)

    for f in preview_data["files"]:
        file_path = os.path.join(temp_folder, f["uvl_filename"])
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        content_bytes = base64.b64decode(f["content_b64"])
        with open(file_path, "wb") as f_out:
            f_out.write(content_bytes)

    serializable_preview = preview_data.copy()
    serializable_preview["publication_type"] = str(preview_data["publication_type"].value)
    session["preview_data"] = serializable_preview

    return render_template("uploader/upload_preview.html", dataset=preview_data)



@uploader_bp.route("/uploader/confirm", methods=["POST"])
@login_required
def confirm_upload():
    preview_data = session.pop("preview_data", None)
    description = request.form.get("dataset_description", "").strip()

    if not preview_data:
        flash("Preview data missing. Try again.", "danger")
        return redirect(url_for("uploader.index"))

    if not description:
        flash("La descripción no puede estar vacía.", "danger")
        return redirect(url_for('uploader.review_upload'))

    if len(description) < 3:
        flash("La descripción debe tener al menos 3 caracteres.", "danger")
        return redirect(url_for('uploader.review_upload'))

    preview_data["title"] = request.form.get("dataset_title")
    preview_data["description"] = request.form.get("dataset_description")
    preview_data["publication_type"] = PublicationType(request.form.get("dataset_publication_type"))
    preview_data["tags"] = request.form.get("dataset_tags")

    for i, f in enumerate(preview_data["files"]):
        f["title"] = request.form.get(f"title_{i}")
        f["description"] = request.form.get(f"description_{i}")

    dataset = service.save_confirmed_upload(preview_data, current_user.id)

    return render_template("uploader/upload_result.html", dataset=dataset)

