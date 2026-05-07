from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    text: str


def chunk_text(
    *,
    source_uri: str,
    text: str,
    chunk_size: int = 1200,
    chunk_overlap: int = 150,
) -> list[Chunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be >= 0 and < chunk_size")

    normalized = (text or "").strip()
    if not normalized:
        return []

    chunks: list[Chunk] = []
    step = chunk_size - chunk_overlap
    idx = 0
    start = 0
    while start < len(normalized):
        part = normalized[start : start + chunk_size].strip()
        if not part:
            break
        digest = hashlib.sha1(f"{source_uri}:{idx}".encode("utf-8")).hexdigest()[:16]
        chunks.append(Chunk(chunk_id=digest, text=part))
        idx += 1
        start += step

    return chunks

