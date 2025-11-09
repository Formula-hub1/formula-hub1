from app.modules.uploader.models import Uploader
from core.repositories.BaseRepository import BaseRepository


class UploaderRepository(BaseRepository):
    def __init__(self):
        super().__init__(Uploader)
