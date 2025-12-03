import base64
import hashlib
import io
import os
import shutil
import zipfile
from pathlib import Path

import requests
from flask_login import current_user

from app import db
from app.modules.dataset.models import DataSet, DSMetaData, PublicationType
from app.modules.featuremodel.models import FeatureModel, FMMetaData
from app.modules.hubfile.models import Hubfile
from core.services.BaseService import BaseService


def calculate_checksum_and_size_bytes(content_bytes):
    checksum = hashlib.sha256(content_bytes).hexdigest()
    size = len(content_bytes)
    return checksum, size


class UploaderService(BaseService):

    def __init__(self):
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        self.base_upload_dir = project_root / "uploads"
        self.base_upload_dir.mkdir(parents=True, exist_ok=True)

    def prepare_preview(self, file, github_url):
        """Genera preview de ZIP o GitHub sin guardar en DB."""
        if file and file.filename:
            return self._prepare_zip_preview(file.read(), file.filename)

        if github_url:
            r = requests.get(github_url)
            if r.status_code != 200:
                raise ValueError("GitHub URL no descargable")
            return self._prepare_zip_preview(r.content, github_url)

        raise ValueError("No ZIP o GitHub URL proporcionado.")

    def _prepare_zip_preview(self, raw_bytes, source_name):
        zf = zipfile.ZipFile(io.BytesIO(raw_bytes))

        files = []
        for name in zf.namelist():
            if name.endswith(".uvl"):
                content = zf.read(name)
                files.append(
                    {
                        "uvl_filename": name,
                        "content_b64": base64.b64encode(content).decode("utf-8"),
                        "title": name,
                        "description": "",
                    }
                )

        if not files:
            raise ValueError("No se encontraron archivos .uvl en el ZIP")

        return {
            "title": source_name,
            "description": "",
            "publication_type": PublicationType.OTHER,
            "tags": "",
            "files": files,
        }

    def save_confirmed_upload(self, data, user_id):
        """Crea la publicación en DB y guarda los archivos."""

        ds_meta = DSMetaData(
            title=data["title"],
            description=data["description"],
            publication_type=data["publication_type"],
            tags=data["tags"],
        )
        db.session.add(ds_meta)
        db.session.commit()

        dataset = DataSet(user_id=user_id, ds_meta_data_id=ds_meta.id)
        db.session.add(dataset)
        db.session.commit()

        user_dir = self.base_upload_dir / f"user_{user_id}"
        dataset_dir = user_dir / f"dataset_{dataset.id}"
        dataset_dir.mkdir(parents=True, exist_ok=True)

        temp_dir = current_user.temp_folder()
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir, exist_ok=True)

        for f in data["files"]:
            content_bytes = base64.b64decode(f["content_b64"])

            fm_meta = FMMetaData(
                uvl_filename=f["uvl_filename"],
                title=f["title"],
                description=f["description"],
                publication_type=data["publication_type"],
            )
            db.session.add(fm_meta)
            db.session.commit()

            fm = FeatureModel(data_set_id=dataset.id, fm_meta_data_id=fm_meta.id)
            db.session.add(fm)
            db.session.commit()

            file_path = dataset_dir / f["uvl_filename"]
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "wb") as f_out:
                f_out.write(content_bytes)

            temp_file_path = Path(temp_dir) / f["uvl_filename"]
            temp_file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(temp_file_path, "wb") as f_temp:
                f_temp.write(content_bytes)

            checksum, size = calculate_checksum_and_size_bytes(content_bytes)

            hubfile = Hubfile(
                name=f["uvl_filename"],
                checksum=checksum,
                size=size,
                feature_model_id=fm.id,
            )
            db.session.add(hubfile)
            db.session.commit()

        return dataset
