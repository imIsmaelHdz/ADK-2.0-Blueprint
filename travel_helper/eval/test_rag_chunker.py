from travel_helper.rag.ingest.chunker import chunk_text


def test_chunk_text_is_deterministic():
    text = "a" * 5000
    a = chunk_text(source_uri="gs://b/x.txt", text=text, chunk_size=1000, chunk_overlap=100)
    b = chunk_text(source_uri="gs://b/x.txt", text=text, chunk_size=1000, chunk_overlap=100)
    assert [c.chunk_id for c in a] == [c.chunk_id for c in b]
    assert [c.text for c in a] == [c.text for c in b]


def test_chunk_id_changes_when_chunk_text_changes():
    # Chunk must include differing text (small windows can yield identical first slices).
    a = chunk_text(
        source_uri="gs://b/x.txt",
        text="hello world unique A tail",
        chunk_size=100,
        chunk_overlap=0,
    )
    b = chunk_text(
        source_uri="gs://b/x.txt",
        text="hello world unique B tail",
        chunk_size=100,
        chunk_overlap=0,
    )
    assert a and b
    assert a[0].chunk_id != b[0].chunk_id


def test_chunk_id_changes_when_chunking_params_change():
    text = "a" * 100
    a = chunk_text(source_uri="gs://b/x.txt", text=text, chunk_size=40, chunk_overlap=5)
    b = chunk_text(source_uri="gs://b/x.txt", text=text, chunk_size=50, chunk_overlap=5)
    assert a and b
    assert a[0].chunk_id != b[0].chunk_id


def test_chunk_text_validates_params():
    try:
        chunk_text(source_uri="s", text="hi", chunk_size=0, chunk_overlap=0)
        assert False, "expected ValueError"
    except ValueError:
        pass

    try:
        chunk_text(source_uri="s", text="hi", chunk_size=10, chunk_overlap=10)
        assert False, "expected ValueError"
    except ValueError:
        pass

