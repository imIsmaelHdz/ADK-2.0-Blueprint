# Travel Helper — RAG with Vertex AI Vector Search 2.0

This repo includes an optional RAG path for travel research: the `rag_search_agent` sub-agent retrieves from an internal document collection stored in **Vertex AI Vector Search 2.0** (instead of using `google_search` on the public internet).

## High-level architecture

- **Indexing (one-time + incremental)**: documents live in GCS, are chunked, and ingested into a Vector Search 2.0 **Collection** configured with **auto-embeddings** (`gemini-embedding-001`).
- **Query-time**: the agent calls `rag_search_documents()` which runs **Hybrid Search** (SemanticSearch + TextSearch) and merges results via **RRF**.

## Prerequisites

- Vertex AI enabled in your GCP project.
- Application Default Credentials (ADC) available locally:

```shell
gcloud auth application-default login
```

## Configuration

Set these environment variables (recommended via `.env` at repo root):

- `GOOGLE_CLOUD_PROJECT`
- `GOOGLE_CLOUD_LOCATION` (e.g. `us-central1`)
- `TRAVEL_HELPER_USE_RAG=1`
- `TRAVEL_HELPER_RAG_COLLECTION_ID` (your collection name)
- `TRAVEL_HELPER_RAG_GCS_URI=gs://bucket/prefix` (documents source)
- `TRAVEL_HELPER_RAG_EMBEDDING_FIELD=content_embedding` (optional; default is `content_embedding`)

## Create the collection (auto-embeddings)

The collection is created with:
- a data schema containing `title`, `source_uri`, `chunk_id`, `mime_type`, `content`
- a vector schema that auto-embeds `content` using `gemini-embedding-001`

You can run the creation step as part of ingestion (next section) or call:

```shell
python3 -c "from travel_helper.rag.config import RagConfig; from travel_helper.rag.ingest.index_admin import create_collection_if_missing; create_collection_if_missing(RagConfig.from_env()); print('ok')"
```

## Ingest documents from GCS

### Quick test with a sample document

This repo includes a small sample doc at [`rag/sample_docs/travel_basics_london.txt`](../rag/sample_docs/travel_basics_london.txt).

Upload it to your GCS prefix:

```shell
gsutil cp travel_helper/rag/sample_docs/travel_basics_london.txt "$TRAVEL_HELPER_RAG_GCS_URI"
```

Then ingest:

```shell
python3 -m travel_helper.rag.ingest.ingest
```

This will:
- list GCS objects under `TRAVEL_HELPER_RAG_GCS_URI`
- load `.txt`, `.md`, `.html` files
- chunk text (size/overlap)
- upload Data Objects with `vectors={}` to trigger auto-embedding generation

## Use RAG in the travel_helper agent

When `TRAVEL_HELPER_USE_RAG=1`, the root agent routes research tasks to the `rag_search_agent` sub-agent.

If RAG env vars are missing while enabled, `rag_search_documents` will raise a clear error so you can fix configuration.

## Do I need a richer metadata filter schema?

Not to test the end-to-end workflow.

- For a basic demo, a single `content` field (plus `title`/`source_uri`) is enough to prove: ingest → auto-embeddings → hybrid search → ADK tool call.
- You only need richer metadata and filters if you want “agentic” constraint handling like: price caps, neighborhoods, date ranges, categories, or per-document access controls.

