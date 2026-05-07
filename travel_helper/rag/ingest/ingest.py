from __future__ import annotations

from dataclasses import dataclass

from travel_helper.rag.config import RagConfig
from travel_helper.rag.ingest.chunker import chunk_text
from travel_helper.rag.ingest.gcs_loader import iter_gcs_documents


@dataclass(frozen=True)
class IngestStats:
    documents: int
    chunks: int


def ingest_from_gcs(cfg: RagConfig, *, max_files: int | None = None) -> IngestStats:
    """
    Load documents from GCS, chunk them, and batch-create Data Objects with empty `vectors`
    to trigger Vector Search 2.0 auto-embedding generation.
    """
    from google.cloud import vectorsearch_v1beta as vectorsearch

    cfg.validate_for_query()
    if not cfg.gcs_uri:
        raise RuntimeError("Missing TRAVEL_HELPER_RAG_GCS_URI for ingestion.")

    data_client = vectorsearch.DataObjectServiceClient()

    docs = 0
    chunks_total = 0

    # Vector Search 2.0 docs recommend batching (article mentions max 250 per request for gemini-embedding-001).
    # `requests` is a repeated field of CreateDataObjectRequest.
    batch: list[vectorsearch.CreateDataObjectRequest] = []

    def flush():
        nonlocal batch
        if not batch:
            return
        req = vectorsearch.BatchCreateDataObjectsRequest(
            parent=cfg.collection_parent,
            requests=batch,
        )
        data_client.batch_create_data_objects(request=req)
        batch = []

    for doc in iter_gcs_documents(cfg.gcs_uri, max_files=max_files):
        docs += 1
        chunks = chunk_text(source_uri=doc.source_uri, text=doc.text)
        for ch in chunks:
            chunks_total += 1

            # Empty vectors triggers auto embedding generation.
            data_object = vectorsearch.DataObject(
                data={
                    "title": doc.title,
                    "source_uri": doc.source_uri,
                    "chunk_id": ch.chunk_id,
                    "mime_type": doc.mime_type,
                    "content": ch.text,
                },
                vectors={},
            )
            batch.append(
                vectorsearch.CreateDataObjectRequest(
                    data_object_id=f"{ch.chunk_id}",
                    data_object=data_object,
                )
            )
            if len(batch) >= 200:
                flush()

    flush()
    return IngestStats(documents=docs, chunks=chunks_total)


if __name__ == "__main__":  # pragma: no cover
    cfg = RagConfig.from_env()
    from travel_helper.rag.ingest.index_admin import create_collection_if_missing

    create_collection_if_missing(cfg)
    stats = ingest_from_gcs(cfg)
    print(f"Ingested documents={stats.documents} chunks={stats.chunks}")

