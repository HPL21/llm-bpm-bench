import io
from typing import List

from fastapi import UploadFile
from minio import Minio

from app.core.config import settings
from app.core.minio_client import client as minio_client


class StorageService:
    """
    Service responsible for high-level interaction with MinIO object storage.
    Separates business logic (like bucket checks) from the raw client connection.
    """

    def __init__(self, client: Minio) -> None:
        self.client = client
        self.bucket_name = settings.MINIO_BUCKET_NAME
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> None:
        """
        Checks if the configured bucket exists in MinIO.
        If the bucket does not exist, it creates a new one.
        """
        if not self.client.bucket_exists(self.bucket_name):
            self.client.make_bucket(self.bucket_name)
            print(f"Bucket '{self.bucket_name}' created successfully.")

    def create_empty_collection(self, collection_name: str) -> str:
        object_name = f"{collection_name}/.keep"
        self.client.put_object(
            bucket_name=self.bucket_name,
            object_name=object_name,
            data=io.BytesIO(b""),
            length=0,
            content_type="application/x-empty",
        )
        return object_name

    def upload_file(self, file: UploadFile, collection_name: str = "default") -> str:
        """
        Uploads a file stream to the MinIO bucket.

        :param file: The FastAPI UploadFile object containing the file to be uploaded.
        :return: The name of the object stored in the bucket (filename).
        :raises Exception: If the connection to MinIO fails or upload is interrupted.
        """
        content = file.file.read()
        file_size = len(content)
        file_data = io.BytesIO(content)

        object_name = f"{collection_name}/{file.filename}"

        self.client.put_object(
            bucket_name=self.bucket_name,
            object_name=object_name,
            data=file_data,
            length=file_size,
            content_type=file.content_type,  # type: ignore
        )
        return object_name

    def delete_file(self, object_name: str) -> None:
        self.client.remove_object(self.bucket_name, object_name)

    def list_files(self) -> List[str]:
        """
        Retrieves a list of all object names in the configured bucket.

        :return: A list of strings representing filenames in the bucket.
        """
        objects = self.client.list_objects(self.bucket_name)
        return [obj.object_name for obj in objects if obj.object_name]


storage_service = StorageService(client=minio_client)
