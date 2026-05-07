from __future__ import annotations

from travel_helper.rag.config import RagConfig


def create_collection_if_missing(cfg: RagConfig) -> str:
    """
    Create a Vector Search 2.0 Collection configured with auto-embeddings.

    Returns the collection resource name.
    """
    from google.cloud import vectorsearch_v1beta as vectorsearch

    cfg.validate_for_query()

    parent = f"projects/{cfg.project_id}/locations/{cfg.location}"
    collection_path = cfg.collection_parent

    client = vectorsearch.VectorSearchServiceClient()
    try:
        client.get_collection(name=collection_path)
        return collection_path
    except Exception:
        pass

    # Minimal schema: store title/source_uri/content + auto-embedding over content.
    collection_config = {
        "data_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "source_uri": {"type": "string"},
                "chunk_id": {"type": "string"},
                "mime_type": {"type": "string"},
                "content": {"type": "string"},
            },
        },
        "vector_schema": {
            cfg.embedding_field: {
                "dense_vector": {
                    "dimensions": 768,
                    "vertex_embedding_config": {
                        "model_id": "gemini-embedding-001",
                        "text_template": "Title: {title}. Content: {content}.",
                        "task_type": "RETRIEVAL_DOCUMENT",
                    },
                }
            }
        },
    }

    req = vectorsearch.CreateCollectionRequest(
        parent=parent,
        collection_id=cfg.collection_id,
        collection=collection_config,
    )
    op = client.create_collection(request=req)
    op.result()
    return collection_path

