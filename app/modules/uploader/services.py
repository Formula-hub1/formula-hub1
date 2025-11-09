from app.modules.uploader.repositories import UploaderRepository
from core.services.BaseService import BaseService


class UploaderService(BaseService):
    def __init__(self):
        super().__init__(UploaderRepository())
