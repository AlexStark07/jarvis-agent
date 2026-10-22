import pytest
import os
from jarvis.providers import get_provider
from langchain_core.messages import AIMessage

# Explicitly gate this test so it only runs when an explicit LIVE_TEST env is set
@pytest.mark.skipif(os.environ.get("LIVE_TEST") != "1", reason="Live tests disabled")
def test_live_provider_smoke():
    provider = get_provider("openai")
    # Verify the openai key raises error correctly if misconfigured

    response = provider.generate("Say 'Hello Jarvis'", system="You are a helpful assistant.")
    assert isinstance(response, AIMessage)
    assert "hello" in response.content.lower() or "jarvis" in response.content.lower()
