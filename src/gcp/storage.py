from __future__ import annotations

import json
import os
from typing import Any


class GCSDocumentStore:
    def __init__(self, bucket: Any) -> None:
        self._bucket = bucket

    @classmethod
    def from_env(cls) -> GCSDocumentStore:
        from google.cloud import storage  # lazy import

        client = storage.Client()
        return cls(client.bucket(os.environ["GCS_BUCKET_DOCS"]))

    def upload_raw(self, tenant_id: str, doc_id: str, content: bytes, content_type: str = "application/pdf") -> str:
        blob = self._bucket.blob(f"raw/{tenant_id}/{doc_id}")
        blob.upload_from_string(content, content_type=content_type)
        return f"gs://{self._bucket.name}/raw/{tenant_id}/{doc_id}"

    def download_raw(self, gcs_path: str) -> bytes:
        # Accept both "gs://bucket/path" and plain "path"
        if gcs_path.startswith("gs://"):
            blob_name = "/".join(gcs_path.split("/")[3:])
        else:
            blob_name = gcs_path
        return self._bucket.blob(blob_name).download_as_bytes()

    def save_parsed(self, tenant_id: str, doc_id: str, data: dict) -> str:
        blob = self._bucket.blob(f"parsed/{tenant_id}/{doc_id}.json")
        blob.upload_from_string(json.dumps(data, ensure_ascii=False), content_type="application/json")
        return f"gs://{self._bucket.name}/parsed/{tenant_id}/{doc_id}.json"

    def get_parsed(self, tenant_id: str, doc_id: str) -> dict:
        blob = self._bucket.blob(f"parsed/{tenant_id}/{doc_id}.json")
        return json.loads(blob.download_as_text())

    def save_normalized(self, tenant_id: str, doc_id: str, data: dict) -> str:
        blob = self._bucket.blob(f"normalized/{tenant_id}/{doc_id}.json")
        blob.upload_from_string(json.dumps(data, ensure_ascii=False), content_type="application/json")
        return f"gs://{self._bucket.name}/normalized/{tenant_id}/{doc_id}.json"
