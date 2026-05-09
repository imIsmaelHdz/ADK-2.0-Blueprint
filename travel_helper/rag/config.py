from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(name: str, default: str | None = None) -> str | None:
    v = os.environ.get(name)
    if v is None:
        return default
    v = v.strip()
    return v or default


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    raw = _env(name)
    if raw is None:
        return default
    try:
        v = int(raw, 10)
    except ValueError as e:
        raise ValueError(f"{name} must be a positive integer, got {raw!r}") from e
    if v <= 0:
        raise ValueError(f"{name} must be a positive integer, got {raw!r}")
    return v


def _env_float(name: str, default: float) -> float:
    raw = _env(name)
    if raw is None:
        return default
    try:
        v = float(raw)
    except ValueError as e:
        raise ValueError(f"{name} must be a positive number, got {raw!r}") from e
    if v <= 0:
        raise ValueError(f"{name} must be a positive number, got {raw!r}")
    return v


@dataclass(frozen=True)
class RagTimeouts:
    """Per-call RPC / HTTP timeouts for RAG (Vector Search, GCS reads)."""

    search_sec: float
    batch_create_sec: float
    gcs_download_sec: float

    @classmethod
    def from_env(cls) -> "RagTimeouts":
        return cls(
            search_sec=_env_float("TRAVEL_HELPER_RAG_SEARCH_TIMEOUT_SEC", 90.0),
            batch_create_sec=_env_float("TRAVEL_HELPER_RAG_BATCH_CREATE_TIMEOUT_SEC", 180.0),
            gcs_download_sec=_env_float("TRAVEL_HELPER_RAG_GCS_DOWNLOAD_TIMEOUT_SEC", 120.0),
        )


@dataclass(frozen=True)
class RagIngestLimits:
    """Caps for GCS ingestion to limit cost, memory, and run time."""

    max_files: int
    max_list_items: int
    max_bytes_per_doc: int
    max_total_bytes: int

    @classmethod
    def from_env(cls) -> "RagIngestLimits":
        return cls(
            max_files=_env_int("TRAVEL_HELPER_RAG_INGEST_MAX_FILES", 500),
            max_list_items=_env_int("TRAVEL_HELPER_RAG_INGEST_MAX_LIST_ITEMS", 10_000),
            max_bytes_per_doc=_env_int(
                "TRAVEL_HELPER_RAG_INGEST_MAX_BYTES_PER_DOC", 5 * 1024 * 1024
            ),
            max_total_bytes=_env_int(
                "TRAVEL_HELPER_RAG_INGEST_MAX_TOTAL_BYTES", 50 * 1024 * 1024
            ),
        )


@dataclass(frozen=True)
class RagConfig:
    project_id: str
    location: str
    collection_id: str
    embedding_field: str = "content_embedding"
    gcs_uri: str | None = None
    enabled: bool = False
    ingest: RagIngestLimits = field(default_factory=RagIngestLimits.from_env)
    timeouts: RagTimeouts = field(default_factory=RagTimeouts.from_env)

    @classmethod
    def from_env(cls) -> "RagConfig":
        return cls(
            project_id=_env("GOOGLE_CLOUD_PROJECT", "") or "",
            location=_env("GOOGLE_CLOUD_LOCATION", "") or "",
            collection_id=_env("TRAVEL_HELPER_RAG_COLLECTION_ID", "") or "",
            embedding_field=_env("TRAVEL_HELPER_RAG_EMBEDDING_FIELD", "content_embedding")
            or "content_embedding",
            gcs_uri=_env("TRAVEL_HELPER_RAG_GCS_URI"),
            enabled=_env_flag("TRAVEL_HELPER_USE_RAG", default=False),
        )

    def validate_for_query(self) -> None:
        missing = []
        if not self.project_id:
            missing.append("GOOGLE_CLOUD_PROJECT")
        if not self.location:
            missing.append("GOOGLE_CLOUD_LOCATION")
        if not self.collection_id:
            missing.append("TRAVEL_HELPER_RAG_COLLECTION_ID")
        if missing:
            raise RuntimeError(
                "RAG is enabled but required env vars are missing: "
                + ", ".join(missing)
            )

    @property
    def collection_parent(self) -> str:
        return f"projects/{self.project_id}/locations/{self.location}/collections/{self.collection_id}"

