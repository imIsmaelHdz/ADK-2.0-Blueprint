from __future__ import annotations

import json
from typing import Any

from travel_helper.rag.config import RagConfig
from travel_helper.rag.vector_search_client import (
    build_clients,
    execute_batch_search_data_objects,
    parse_search_response,
    semantic_and_text_search_request,
)


def _parse_filter_json(filter: str) -> dict[str, Any] | None:
    if not filter or not filter.strip():
        return None
    return json.loads(filter)


def rag_search_documents(query: str, filter: str = "", top_k: int = 8) -> list[dict[str, Any]]:
    """
    Search internal travel documents using Vertex AI Vector Search 2.0 Hybrid Search.

    Args:
        query: Natural language query string.
        filter: Optional JSON filter expression (Mongo-like operators).
        top_k: Number of results to return.

    Returns:
        List of results, or empty list if collection is not configured (triggers fallback).
    """
    cfg = RagConfig.from_env()
    try:
        cfg.validate_for_query()
    except RuntimeError:
        # Collection not configured yet — return empty so the orchestrator falls back to Google Search.
        return []

    filter_dict = _parse_filter_json(filter)
    clients = build_clients()

    # Minimal set of output fields we expect to store on ingested Data Objects.
    output_fields = [
        "title",
        "source_uri",
        "chunk_id",
        "content",
        "mime_type",
    ]

    request = semantic_and_text_search_request(
        cfg=cfg,
        query=query,
        filter_dict=filter_dict,
        top_k=top_k,
        output_fields=output_fields,
    )

    response = execute_batch_search_data_objects(
        clients.search,
        request,
        timeout_sec=cfg.timeouts.search_sec,
    )
    return parse_search_response(response)

