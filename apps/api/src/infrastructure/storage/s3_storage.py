import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from src.config import get_settings
from src.domain.shared.exceptions import StorageUnavailableError
from src.domain.shared.storage_port import ObjectStat

settings = get_settings()


class S3StorageProvider:
    def __init__(self) -> None:
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            config=Config(
                signature_version="s3v4",
                connect_timeout=3,
                read_timeout=5,
                retries={"max_attempts": 1},
            ),
        )
        self._bucket = settings.s3_bucket

    def upload_url(self, *, key: str, content_type: str, expires_in: int) -> str:
        return self._client.generate_presigned_url(
            "put_object",
            Params={"Bucket": self._bucket, "Key": key, "ContentType": content_type},
            ExpiresIn=expires_in,
        )

    def download_url(self, *, key: str, expires_in: int) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in,
        )

    def stat(self, *, key: str) -> ObjectStat | None:
        try:
            response = self._client.head_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchKey"):
                return None
            raise
        except BotoCoreError as exc:
            raise StorageUnavailableError(str(exc)) from exc
        return ObjectStat(
            size_bytes=response["ContentLength"],
            content_type=response.get("ContentType"),
        )

    def put_object(self, *, key: str, data: bytes, content_type: str) -> None:
        try:
            self._client.put_object(
                Bucket=self._bucket, Key=key, Body=data, ContentType=content_type
            )
        except BotoCoreError as exc:
            raise StorageUnavailableError(str(exc)) from exc

    def get_object(self, *, key: str) -> bytes:
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
            return response["Body"].read()
        except BotoCoreError as exc:
            raise StorageUnavailableError(str(exc)) from exc


_provider: S3StorageProvider | None = None


def get_storage_provider() -> S3StorageProvider:
    global _provider
    if _provider is None:
        _provider = S3StorageProvider()
    return _provider
