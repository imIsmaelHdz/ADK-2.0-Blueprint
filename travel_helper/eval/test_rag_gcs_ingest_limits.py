from unittest.mock import MagicMock, patch

import pytest

from travel_helper.rag.config import RagIngestLimits
from travel_helper.rag.ingest.gcs_loader import iter_gcs_documents


def _txt_blob(name: str, *, size: int, body: bytes) -> MagicMock:
    b = MagicMock()
    b.name = name
    b.content_type = "text/plain"
    b.size = size
    b.download_as_bytes.return_value = body
    b.reload.return_value = None
    return b


def _make_client(blobs: list) -> MagicMock:
    client = MagicMock()
    bucket = MagicMock()

    def list_blobs(_bucket, prefix=""):
        return iter(blobs)

    client.list_blobs.side_effect = list_blobs
    client.bucket.return_value = bucket
    return client


@patch("travel_helper.rag.ingest.gcs_loader.storage.Client")
def test_iter_gcs_respects_max_list_items(mock_client_cls):
    limits = RagIngestLimits(
        max_files=100,
        max_list_items=3,
        max_bytes_per_doc=10_000,
        max_total_bytes=1_000_000,
    )
    blobs = [
        _txt_blob("a.txt", size=3, body=b"aaa"),
        _txt_blob("b.txt", size=3, body=b"bbb"),
        _txt_blob("c.txt", size=3, body=b"ccc"),
        _txt_blob("d.txt", size=3, body=b"ddd"),
    ]
    mock_client_cls.return_value = _make_client(blobs)

    with pytest.raises(RuntimeError, match="Ingest aborted"):
        list(iter_gcs_documents("gs://bucket/prefix/", limits=limits))


@patch("travel_helper.rag.ingest.gcs_loader.storage.Client")
def test_iter_gcs_skipped_suffixes_count_toward_list_cap(mock_client_cls):
    limits = RagIngestLimits(
        max_files=10,
        max_list_items=4,
        max_bytes_per_doc=10_000,
        max_total_bytes=1_000_000,
    )
    blobs = [
        MagicMock(name="x.bin", content_type=None, size=1),
        MagicMock(name="y.bin", content_type=None, size=1),
        MagicMock(name="z.bin", content_type=None, size=1),
        MagicMock(name="w.bin", content_type=None, size=1),
        MagicMock(name="a.txt", size=2, content_type="text/plain"),
    ]
    for b in blobs:
        b.reload.return_value = None
    blobs[-1].download_as_bytes.return_value = b"ok"

    mock_client_cls.return_value = _make_client(blobs)

    with pytest.raises(RuntimeError, match="Ingest aborted"):
        list(iter_gcs_documents("gs://bucket/prefix/", limits=limits))


@patch("travel_helper.rag.ingest.gcs_loader.storage.Client")
def test_iter_gcs_rejects_oversized_object(mock_client_cls):
    limits = RagIngestLimits(
        max_files=10,
        max_list_items=100,
        max_bytes_per_doc=10,
        max_total_bytes=1_000_000,
    )
    blobs = [_txt_blob("big.txt", size=500, body=b"x" * 500)]
    mock_client_cls.return_value = _make_client(blobs)

    with pytest.raises(RuntimeError, match="TRAVEL_HELPER_RAG_INGEST_MAX_BYTES_PER_DOC"):
        list(iter_gcs_documents("gs://bucket/prefix/", limits=limits))


@patch("travel_helper.rag.ingest.gcs_loader.storage.Client")
def test_iter_gcs_rejects_aggregate_over_total_bytes(mock_client_cls):
    limits = RagIngestLimits(
        max_files=10,
        max_list_items=100,
        max_bytes_per_doc=100,
        max_total_bytes=50,
    )
    blobs = [
        _txt_blob("a.txt", size=30, body=b"a" * 30),
        _txt_blob("b.txt", size=30, body=b"b" * 30),
    ]
    mock_client_cls.return_value = _make_client(blobs)

    with pytest.raises(RuntimeError, match="MAX_TOTAL_BYTES"):
        list(iter_gcs_documents("gs://bucket/prefix/", limits=limits))


@patch("travel_helper.rag.ingest.gcs_loader.storage.Client")
def test_iter_gcs_max_files_override_tightens_cap(mock_client_cls):
    limits = RagIngestLimits(
        max_files=5,
        max_list_items=100,
        max_bytes_per_doc=1000,
        max_total_bytes=100_000,
    )
    blobs = [_txt_blob(f"{i}.txt", size=2, body=b"xx") for i in range(10)]
    mock_client_cls.return_value = _make_client(blobs)

    out = list(iter_gcs_documents("gs://bucket/prefix/", limits=limits, max_files=2))
    assert len(out) == 2
