from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import json

from travel_helper.rag.config import RagConfig


def _import_vectorsearch():
    try:
        # Provided by `google-cloud-vectorsearch`
        from google.cloud import vectorsearch_v1beta  # type: ignore

        return vectorsearch_v1beta
    except Exception as e:  # pragma: no cover
        raise ImportError(
            "Vector Search client is not installed. Install `google-cloud-vectorsearch`."
        ) from e


@dataclass(frozen=True)
class VectorSearchClients:
    admin: Any
    data: Any
    search: Any
    vectorsearch: Any


def build_clients() -> VectorSearchClients:
    vectorsearch = _import_vectorsearch()

    # NOTE: the exact client class names are from the public library API.
    admin = vectorsearch.VectorSearchServiceClient()
    data = vectorsearch.DataObjectServiceClient()
    # Query/search API is exposed via DataObjectSearchServiceClient in google-cloud-vectorsearch.
    search = vectorsearch.DataObjectSearchServiceClient()
    return VectorSearchClients(admin=admin, data=data, search=search, vectorsearch=vectorsearch)


def semantic_and_text_search_request(
    *,
    cfg: RagConfig,
    query: str,
    filter_dict: dict | None,
    top_k: int,
    output_fields: Iterable[str],
    semantic_weight: float = 0.6,
    text_weight: float = 0.4,
) -> Any:
    vectorsearch = _import_vectorsearch()

    collection_parent = cfg.collection_parent

    semantic_kwargs: dict[str, Any] = {
        "search_text": query,
        "search_field": cfg.embedding_field,
        "task_type": "QUESTION_ANSWERING",
        "top_k": top_k,
        "output_fields": vectorsearch.OutputFields(data_fields=list(output_fields)),
    }
    if filter_dict is not None:
        semantic_kwargs["filter"] = filter_dict

    semantic = vectorsearch.SemanticSearch(**semantic_kwargs)

    text_kwargs: dict[str, Any] = {
        "search_text": query,
        "data_field_names": list(output_fields),
        "top_k": top_k,
        "output_fields": vectorsearch.OutputFields(data_fields=list(output_fields)),
    }
    if filter_dict is not None:
        text_kwargs["filter"] = filter_dict

    text = vectorsearch.TextSearch(**text_kwargs)

    request = vectorsearch.BatchSearchDataObjectsRequest(
        parent=collection_parent,
        searches=[
            vectorsearch.Search(semantic_search=semantic),
            vectorsearch.Search(text_search=text),
        ],
        combine=vectorsearch.BatchSearchDataObjectsRequest.CombineResultsOptions(
            ranker=vectorsearch.Ranker(
                rrf=vectorsearch.ReciprocalRankFusion(weights=[semantic_weight, text_weight])
            )
        ),
    )
    return request


def parse_search_response(response: Any) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    # Response shape can vary slightly by library versions; handle common patterns.
    batch_results = getattr(response, "results", None) or []
    if not batch_results:
        return results

    first = batch_results[0]
    per_results = getattr(first, "results", None) or []
    for res in per_results:
        data_object = getattr(res, "data_object", None)
        data = getattr(data_object, "data", None) if data_object else None
        # Vector Search 2.0 responses use `distance` (smaller is closer).
        score = getattr(res, "distance", None)

        # `data` is a protobuf Struct-like object; convert to a plain dict.
        data_dict: dict[str, Any] = {}
        if data is not None:
            try:
                from google.protobuf.json_format import MessageToDict
                pb = getattr(data, "_pb", data)
                # Some proto-plus wrappers expose Struct as a map container rather than a message.
                if not hasattr(pb, "DESCRIPTOR") and hasattr(pb, "items"):
                    raise TypeError("Struct is represented as fields map container")

                data_dict = MessageToDict(pb, preserving_proto_field_name=True)  # type: ignore[arg-type]
            except Exception:
                # Fall back to best-effort extraction from Struct fields.
                pb = getattr(data, "_pb", None)
                # Case 1: map container of {key: Value}
                if pb is not None and hasattr(pb, "items"):
                    extracted: dict[str, Any] = {}
                    for k, v in pb.items():  # type: ignore[union-attr]
                        kind = v.WhichOneof("kind")
                        if kind == "string_value":
                            extracted[str(k)] = v.string_value
                        elif kind == "number_value":
                            extracted[str(k)] = v.number_value
                        elif kind == "bool_value":
                            extracted[str(k)] = v.bool_value
                        elif kind == "null_value":
                            extracted[str(k)] = None
                        else:
                            extracted[str(k)] = str(v)
                    data_dict = extracted
                # Case 2: actual Struct message with .fields mapping
                else:
                    fields = getattr(pb, "fields", None) if pb is not None else None
                    if isinstance(fields, dict):
                        extracted = {}
                        for k, v in fields.items():
                            kind = v.WhichOneof("kind")
                            if kind == "string_value":
                                extracted[k] = v.string_value
                            elif kind == "number_value":
                                extracted[k] = v.number_value
                            elif kind == "bool_value":
                                extracted[k] = v.bool_value
                            elif kind == "null_value":
                                extracted[k] = None
                            else:
                                extracted[k] = str(v)
                        data_dict = extracted
                    else:
                        data_dict = {}

        if not isinstance(data_dict, dict) or not data_dict:
            continue
        results.append(
            {
                "title": data_dict.get("title") or data_dict.get("name"),
                "source_uri": data_dict.get("source_uri") or data_dict.get("url"),
                "snippet": data_dict.get("snippet") or data_dict.get("content"),
                "score": score,
                "metadata": _json_sanitize(
                    {k: v for k, v in data_dict.items() if k not in ("content", "snippet")}
                ),
            }
        )
    return results


def _json_sanitize(value: Any) -> Any:
    """Ensure nested structures are JSON-serializable (best-effort)."""
    try:
        json.dumps(value)
        return value
    except TypeError:
        if isinstance(value, dict):
            return {str(k): _json_sanitize(v) for k, v in value.items()}
        if isinstance(value, list):
            return [_json_sanitize(v) for v in value]
        return str(value)

