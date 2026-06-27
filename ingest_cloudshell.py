"""
Self-contained RAG ingest script for Cloud Shell.
Run with:
  python ingest_cloudshell.py
"""

import hashlib
import os

PROJECT    = "adk2-495619"
LOCATION   = "us-central1"
COLLECTION = "travel-helper-docs"
GCS_URI    = "gs://adk2-495619-travel-docs/"
EMB_FIELD  = "content_embedding"
CHUNK_SIZE    = 1200
CHUNK_OVERLAP = 150
BATCH_SIZE    = 200

os.environ.setdefault("GOOGLE_CLOUD_PROJECT", PROJECT)
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", LOCATION)


# ── helpers ────────────────────────────────────────────────────────────────

def chunk_text(source_uri, text):
    chunks = []
    normalized = (text or "").strip()
    step = CHUNK_SIZE - CHUNK_OVERLAP
    idx = 0
    start = 0
    while start < len(normalized):
        part = normalized[start:start + CHUNK_SIZE].strip()
        if not part:
            break
        h = hashlib.sha256()
        h.update(source_uri.encode())
        h.update(b"\xff")
        h.update(str(idx).encode())
        h.update(b"\xff")
        h.update(part.encode())
        chunk_id = h.hexdigest()[:32]
        chunks.append((chunk_id, part))
        idx += 1
        start += step
    return chunks


TEXT_EXTENSIONS = {".txt", ".md", ".html", ".htm", ".csv"}

def load_gcs_docs(gcs_uri):
    from google.cloud import storage
    import os as _os
    if not gcs_uri.startswith("gs://"):
        raise ValueError("Expected gs://bucket/prefix")
    rest = gcs_uri[5:]
    bucket_name, _, prefix = rest.partition("/")
    client = storage.Client(project=PROJECT)
    bucket = client.bucket(bucket_name)
    docs = []
    for blob in bucket.list_blobs(prefix=prefix or None):
        if blob.size == 0:
            continue
        ext = _os.path.splitext(blob.name)[1].lower()
        if ext not in TEXT_EXTENSIONS:
            print(f"  Skipping (not a text file): {blob.name}")
            continue
        text = blob.download_as_text(encoding="utf-8", timeout=120)
        source_uri = f"gs://{bucket_name}/{blob.name}"
        title = blob.name.split("/")[-1]
        docs.append((source_uri, title, "text/plain", text))
        print(f"  Loaded: {source_uri} ({len(text)} chars)")
    return docs


# ── collection ─────────────────────────────────────────────────────────────

def create_collection_if_missing(vs):
    parent = f"projects/{PROJECT}/locations/{LOCATION}"
    collection_path = f"{parent}/collections/{COLLECTION}"
    client = vs.VectorSearchServiceClient()
    try:
        client.get_collection(name=collection_path)
        print(f"Collection already exists: {collection_path}")
        return collection_path
    except Exception:
        pass

    print(f"Creating collection: {COLLECTION} ...")
    req = vs.CreateCollectionRequest(
        parent=parent,
        collection_id=COLLECTION,
        collection={
            "data_schema": {
                "type": "object",
                "properties": {
                    "title":      {"type": "string"},
                    "source_uri": {"type": "string"},
                    "chunk_id":   {"type": "string"},
                    "mime_type":  {"type": "string"},
                    "content":    {"type": "string"},
                },
            },
            "vector_schema": {
                EMB_FIELD: {
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
        },
    )
    op = client.create_collection(request=req)
    result = op.result(timeout=300)
    print(f"Collection created: {result.name}")
    return collection_path


# ── ingest ─────────────────────────────────────────────────────────────────

def ingest(vs, collection_path):
    data_client = vs.DataObjectServiceClient()
    docs = load_gcs_docs(GCS_URI)
    if not docs:
        print("No documents found in GCS URI.")
        return

    batch = []
    total_chunks = 0

    def flush():
        if not batch:
            return
        req = vs.BatchCreateDataObjectsRequest(
            parent=collection_path,
            requests=batch,
        )
        try:
            data_client.batch_create_data_objects(request=req, timeout=180)
            print(f"  Indexed {len(batch)} chunks")
        except Exception as e:
            if "AlreadyExists" in type(e).__name__ or "ALREADY_EXISTS" in str(e):
                print(f"  Chunks already exist — upserting individually...")
                for r in batch:
                    try:
                        data_client.upsert_data_object(
                            request=vs.UpsertDataObjectRequest(
                                parent=collection_path,
                                data_object_id=r.data_object_id,
                                data_object=r.data_object,
                            ),
                            timeout=60,
                        )
                    except Exception:
                        pass
                print(f"  Upserted {len(batch)} chunks")
            else:
                raise
        batch.clear()

    for source_uri, title, mime_type, text in docs:
        chunks = chunk_text(source_uri, text)
        print(f"  Chunked '{title}' → {len(chunks)} chunk(s)")
        for chunk_id, chunk_text_val in chunks:
            total_chunks += 1
            data_object = vs.DataObject(
                data={
                    "title":      title,
                    "source_uri": source_uri,
                    "chunk_id":   chunk_id,
                    "mime_type":  mime_type,
                    "content":    chunk_text_val,
                },
                vectors={},   # empty → triggers auto-embedding
            )
            batch.append(vs.CreateDataObjectRequest(
                data_object_id=chunk_id,
                data_object=data_object,
            ))
            if len(batch) >= BATCH_SIZE:
                flush()

    flush()
    print(f"\nDone. documents={len(docs)} chunks={total_chunks}")


# ── main ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Installing dependencies...")
    import subprocess, sys
    subprocess.check_call([
        sys.executable, "-m", "pip", "install",
        "google-cloud-vectorsearch", "google-cloud-storage",
        "--break-system-packages", "-q"
    ])
    # Re-exec so the newly installed packages are on sys.path
    import importlib
    try:
        from google.cloud import vectorsearch_v1beta as vs
    except ImportError:
        print("Re-launching with refreshed sys.path...")
        os.execv(sys.executable, [sys.executable] + sys.argv)

    from google.cloud import vectorsearch_v1beta as vs

    print(f"\nProject  : {PROJECT}")
    print(f"Location : {LOCATION}")
    print(f"Collection: {COLLECTION}")
    print(f"GCS URI  : {GCS_URI}\n")

    collection_path = create_collection_if_missing(vs)
    ingest(vs, collection_path)
