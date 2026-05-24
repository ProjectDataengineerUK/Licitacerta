"""Unit tests for GCSDocumentStore — no real GCP calls."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from src.gcp.storage import GCSDocumentStore


@pytest.fixture
def mock_bucket():
    bucket = MagicMock()
    bucket.name = "test-bucket"
    blob = MagicMock()
    bucket.blob.return_value = blob
    blob.download_as_bytes.return_value = b"%PDF-1.4 test"
    blob.download_as_text.return_value = json.dumps({"doc_id": "doc-abc", "pages": []})
    return bucket, blob


def test_upload_raw_returns_gcs_path(mock_bucket):
    bucket, blob = mock_bucket
    store = GCSDocumentStore(bucket)
    path = store.upload_raw("tenant-1", "doc-abc", b"%PDF-1.4 test")

    assert path == "gs://test-bucket/raw/tenant-1/doc-abc"
    bucket.blob.assert_called_once_with("raw/tenant-1/doc-abc")
    blob.upload_from_string.assert_called_once_with(b"%PDF-1.4 test", content_type="application/pdf")


def test_download_raw_strips_gs_prefix(mock_bucket):
    bucket, blob = mock_bucket
    store = GCSDocumentStore(bucket)
    content = store.download_raw("gs://test-bucket/raw/tenant-1/doc-abc")

    assert content == b"%PDF-1.4 test"
    bucket.blob.assert_called_once_with("raw/tenant-1/doc-abc")


def test_save_parsed_returns_gcs_path(mock_bucket):
    bucket, blob = mock_bucket
    store = GCSDocumentStore(bucket)
    data = {"doc_id": "doc-abc", "pages": []}

    path = store.save_parsed("tenant-1", "doc-abc", data)

    assert path == "gs://test-bucket/parsed/tenant-1/doc-abc.json"
    blob.upload_from_string.assert_called_once_with(
        json.dumps(data, ensure_ascii=False),
        content_type="application/json",
    )


def test_get_parsed_returns_dict(mock_bucket):
    bucket, blob = mock_bucket
    store = GCSDocumentStore(bucket)
    result = store.get_parsed("tenant-1", "doc-abc")

    assert result == {"doc_id": "doc-abc", "pages": []}
    bucket.blob.assert_called_once_with("parsed/tenant-1/doc-abc.json")


def test_save_normalized(mock_bucket):
    bucket, blob = mock_bucket
    store = GCSDocumentStore(bucket)
    path = store.save_normalized("tenant-1", "doc-abc", {"key": "value"})

    assert path == "gs://test-bucket/normalized/tenant-1/doc-abc.json"
