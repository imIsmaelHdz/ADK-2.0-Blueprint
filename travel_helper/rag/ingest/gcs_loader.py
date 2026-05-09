from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from typing import Iterator

from google.api_core import exceptions as gexc
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError

from travel_helper.rag.config import RagIngestLimits


@dataclass(frozen=True)
class GcsDocument:
    source_uri: str
    title: str
    mime_type: str
    text: str


def _parse_gs_uri(gs_uri: str) -> tuple[str, str]:
    if not gs_uri.startswith("gs://"):
        raise ValueError("Expected a gs://bucket/prefix URI")
    rest = gs_uri[len("gs://") :]
    if "/" not in rest:
        return rest, ""
    bucket, prefix = rest.split("/", 1)
    return bucket, prefix


def iter_gcs_documents(
    gs_uri: str,
    *,
    limits: RagIngestLimits,
    max_files: int | None = None,
    download_timeout_sec: float | None = None,
) -> Iterator[GcsDocument]:
    """
    Yield text-like documents under a GCS prefix with strict caps on listing,
    per-object size, aggregate bytes, and number of ingested files.

    ``download_timeout_sec`` bounds each ``download_as_bytes`` call (default from
    ``TRAVEL_HELPER_RAG_GCS_DOWNLOAD_TIMEOUT_SEC`` when omitted).
    """
    from travel_helper.rag.config import RagTimeouts

    if download_timeout_sec is None:
        download_timeout_sec = RagTimeouts.from_env().gcs_download_sec

    bucket_name, prefix = _parse_gs_uri(gs_uri)
    file_cap = limits.max_files if max_files is None else min(limits.max_files, max_files)

    client = storage.Client()
    bucket = client.bucket(bucket_name)

    yielded = 0
    list_items = 0
    total_bytes = 0

    for blob in client.list_blobs(bucket, prefix=prefix):
        list_items += 1
        if list_items > limits.max_list_items:
            raise RuntimeError(
                f"Ingest aborted: listed {list_items} GCS objects "
                f"(limit {limits.max_list_items}). Narrow TRAVEL_HELPER_RAG_GCS_URI "
                "or raise TRAVEL_HELPER_RAG_INGEST_MAX_LIST_ITEMS."
            )

        if yielded >= file_cap:
            break

        name = blob.name
        content_type = blob.content_type or mimetypes.guess_type(name)[0] or "text/plain"

        if not (
            name.endswith(".txt")
            or name.endswith(".md")
            or name.endswith(".html")
            or name.endswith(".htm")
        ):
            continue

        if blob.size is None:
            blob.reload()
        if blob.size is None:
            raise RuntimeError(
                f"Cannot determine size for gs://{bucket_name}/{name}; "
                "refusing download. Set object metadata or use smaller objects."
            )
        if blob.size > limits.max_bytes_per_doc:
            raise RuntimeError(
                f"Object gs://{bucket_name}/{name} is {blob.size} bytes "
                f"(limit {limits.max_bytes_per_doc} from "
                "TRAVEL_HELPER_RAG_INGEST_MAX_BYTES_PER_DOC)."
            )
        if total_bytes + blob.size > limits.max_total_bytes:
            raise RuntimeError(
                "Ingest would exceed TRAVEL_HELPER_RAG_INGEST_MAX_TOTAL_BYTES "
                f"({limits.max_total_bytes}); {total_bytes} bytes already scheduled."
            )

        try:
            raw = blob.download_as_bytes(timeout=download_timeout_sec)
        except (gexc.GoogleAPICallError, GoogleCloudError) as e:
            raise RuntimeError(
                f"GCS download failed for gs://{bucket_name}/{name} "
                f"(timeout={download_timeout_sec}s): {e}"
            ) from e
        total_bytes += blob.size
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("utf-8", errors="replace")

        title = name.rsplit("/", 1)[-1]
        yield GcsDocument(
            source_uri=f"gs://{bucket_name}/{name}",
            title=title,
            mime_type=content_type,
            text=text,
        )
        yielded += 1
