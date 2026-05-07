from __future__ import annotations

import os
from dataclasses import dataclass


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


@dataclass(frozen=True)
class RagConfig:
    project_id: str
    location: str
    collection_id: str
    embedding_field: str = "content_embedding"
    gcs_uri: str | None = None
    enabled: bool = False

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

