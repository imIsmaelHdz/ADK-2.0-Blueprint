import os

import pytest

from travel_helper.rag.tools import rag_search_documents


@pytest.mark.skipif(
    not os.environ.get("TRAVEL_HELPER_RAG_INTEGRATION_TESTS"),
    reason="Set TRAVEL_HELPER_RAG_INTEGRATION_TESTS=1 to run live Vector Search query tests",
)
def test_rag_search_documents_live_smoke():
    # Requires all RAG env vars + ADC configured.
    results = rag_search_documents("visa requirements", top_k=2)
    assert isinstance(results, list)

