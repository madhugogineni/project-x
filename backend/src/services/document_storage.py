from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache

from botocore.exceptions import ClientError

from core.security import utc_now
from core.settings import Settings, get_settings


@dataclass(frozen=True)
class PresignedDocumentUrl:
    url: str
    headers: dict[str, str]
    expires_at: datetime


class S3DocumentStorageService:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client = self._build_client()

    def create_upload_url(
        self,
        *,
        object_key: str,
        mime_type: str | None = None,
    ) -> PresignedDocumentUrl:
        params: dict[str, str] = {
            "Bucket": self._settings.s3_bucket_name,
            "Key": object_key,
        }
        headers: dict[str, str] = {}
        if mime_type:
            params["ContentType"] = mime_type
            headers["Content-Type"] = mime_type

        expires_in = self._settings.document_presigned_url_ttl_seconds
        url = self._client.generate_presigned_url(
            "put_object",
            Params=params,
            ExpiresIn=expires_in,
        )
        return PresignedDocumentUrl(
            url=url,
            headers=headers,
            expires_at=utc_now() + timedelta(seconds=expires_in),
        )

    def create_download_url(self, *, object_key: str) -> PresignedDocumentUrl:
        expires_in = self._settings.document_presigned_url_ttl_seconds
        url = self._client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self._settings.s3_bucket_name,
                "Key": object_key,
            },
            ExpiresIn=expires_in,
        )
        return PresignedDocumentUrl(
            url=url,
            headers={},
            expires_at=utc_now() + timedelta(seconds=expires_in),
        )

    def object_exists(self, *, object_key: str) -> bool:
        try:
            self._client.head_object(
                Bucket=self._settings.s3_bucket_name,
                Key=object_key,
            )
        except ClientError:
            return False
        return True

    def _build_client(self):  # type: ignore[no-untyped-def]
        import boto3

        client_kwargs: dict[str, str] = {}
        if self._settings.aws_region:
            client_kwargs["region_name"] = self._settings.aws_region
        if self._settings.s3_endpoint_url:
            client_kwargs["endpoint_url"] = self._settings.s3_endpoint_url
        return boto3.client("s3", **client_kwargs)


@lru_cache
def get_document_storage_service() -> S3DocumentStorageService:
    return S3DocumentStorageService()
