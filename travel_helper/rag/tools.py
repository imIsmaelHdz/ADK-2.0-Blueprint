from __future__ import annotations

import json
from typing import Any

from travel_helper.rag.config import RagConfig
from travel_helper.rag.vector_search_client import (
    build_clients,
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
        List of results containing title, source_uri, snippet, score, metadata.
    """
    cfg = RagConfig.from_env()
    cfg.validate_for_query()

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

    response = clients.search.batch_search_data_objects(request=request)
    return parse_search_response(response)

