from travel_helper.rag.ingest.chunker import chunk_text


def test_chunk_text_is_deterministic():
    text = "a" * 5000
    a = chunk_text(source_uri="gs://b/x.txt", text=text, chunk_size=1000, chunk_overlap=100)
    b = chunk_text(source_uri="gs://b/x.txt", text=text, chunk_size=1000, chunk_overlap=100)
    assert [c.chunk_id for c in a] == [c.chunk_id for c in b]
    assert [c.text for c in a] == [c.text for c in b]


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

