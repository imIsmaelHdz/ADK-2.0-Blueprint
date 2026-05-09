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
        h = hashlib.sha256()
        h.update(source_uri.encode("utf-8"))
        h.update(b"\xff")
        h.update(str(idx).encode("ascii"))
        h.update(b"\xff")
        h.update(str(chunk_size).encode("ascii"))
        h.update(b"\xff")
        h.update(str(chunk_overlap).encode("ascii"))
        h.update(b"\xff")
        h.update(part.encode("utf-8"))
        chunk_id = h.hexdigest()[:32]
        chunks.append(Chunk(chunk_id=chunk_id, text=part))
        idx += 1
        start += step

    return chunks

