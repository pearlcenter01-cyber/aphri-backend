import uuid
import boto3
from botocore.config import Config
from fastapi import UploadFile, HTTPException
from app.config import settings

IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
AUDIO_TYPES = {"audio/m4a", "audio/mp4", "audio/mpeg", "audio/wav", "audio/aac", "audio/x-m4a", "audio/3gpp", "audio/3gpp2"}

MAX_IMAGE_SIZE = 5 * 1024 * 1024
MAX_AUDIO_SIZE = 10 * 1024 * 1024


class StorageService:
    _client = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            cls._client = boto3.client(
                "s3",
                endpoint_url=settings.R2_ENDPOINT,
                aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
                config=Config(signature_version="s3v4"),
                region_name="auto",
            )
        return cls._client

    @classmethod
    async def upload_image(cls, file: UploadFile) -> dict:
        if file.content_type not in IMAGE_TYPES:
            raise HTTPException(400, f"Unsupported image type: {file.content_type}")
        return await cls._upload(file, folder="images", max_size=MAX_IMAGE_SIZE, media_type="image")

    @classmethod
    async def upload_audio(cls, file: UploadFile) -> dict:
        if file.content_type not in AUDIO_TYPES:
            raise HTTPException(400, f"Unsupported audio type: {file.content_type}")
        return await cls._upload(file, folder="audio", max_size=MAX_AUDIO_SIZE, media_type="voice")

    @classmethod
    async def _upload(cls, file: UploadFile, folder: str, max_size: int, media_type: str) -> dict:
        content = await file.read()
        if len(content) > max_size:
            raise HTTPException(400, f"File too large (max {max_size // 1024 // 1024} MB)")

        ext = (file.filename or "file").split(".")[-1].lower()
        if ext not in ("jpg", "jpeg", "png", "webp", "gif", "m4a", "mp4", "mp3", "wav", "aac", "3gp"):
            ext = "bin"

        key = f"{folder}/{uuid.uuid4()}.{ext}"

        client = cls.get_client()
        client.put_object(
            Bucket=settings.R2_BUCKET,
            Key=key,
            Body=content,
            ContentType=file.content_type,
        )

        return {
            "media_url": f"{settings.R2_PUBLIC_URL}/{key}",
            "media_type": media_type,
            "size": len(content),
        }