from abc import ABC, abstractmethod
from typing import Any, Dict, List

class LLMProvider(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    def generate(self, prompt: str, system: str = "", tools: List[Dict[str, Any]] | None = None) -> str:
        """Generate a response given a prompt and optional tools."""
        pass

class MockProvider(LLMProvider):
    """Deterministic mock provider for testing and deterministic local execution."""

    def __init__(self, predefined_responses: Dict[str, str] = None):
        self.predefined_responses = predefined_responses or {}
        self.call_count = 0
        self.last_prompt = ""

    def generate(self, prompt: str, system: str = "", tools: List[Dict[str, Any]] | None = None) -> str:
        self.call_count += 1
        self.last_prompt = prompt

        # Match exact string if defined
        if prompt in self.predefined_responses:
            return self.predefined_responses[prompt]

        # Match keywords for generic deterministic responses
        lower_prompt = prompt.lower()
        if "research" in lower_prompt:
            return "Mock Research Finding: The system supports up to 10 concurrent connections."
        if "test" in lower_prompt:
            return "Mock Developer Action: Executed `pytest` successfully. 20 tests passed."

        return "Mock generic response."

def get_provider(provider_type: str = "mock", config: Dict[str, str] = None) -> LLMProvider:
    """Factory to retrieve configured LLM providers."""
    if provider_type == "mock":
        return MockProvider()
    # In the future, instantiate OpenAIProvider, AnthropicProvider based on config.
    raise ValueError(f"Unsupported provider type: {provider_type}")
