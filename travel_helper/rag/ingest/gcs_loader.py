from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from typing import Iterable, Iterator

from google.cloud import storage


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


def iter_gcs_documents(gs_uri: str, *, max_files: int | None = None) -> Iterator[GcsDocument]:
    bucket_name, prefix = _parse_gs_uri(gs_uri)
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    count = 0
    for blob in client.list_blobs(bucket, prefix=prefix):
        if max_files is not None and count >= max_files:
            break

        name = blob.name
        content_type = blob.content_type or mimetypes.guess_type(name)[0] or "text/plain"

        # Start simple: text-ish docs only.
        if not (
            name.endswith(".txt")
            or name.endswith(".md")
            or name.endswith(".html")
            or name.endswith(".htm")
        ):
            continue

        raw = blob.download_as_bytes()
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
        count += 1

