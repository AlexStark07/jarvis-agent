from abc import ABC, abstractmethod
from typing import Any, Dict, List

class LLMProvider(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    def generate(self, prompt: str, system: str = "", tools: List[Dict[str, Any]] | None = None) -> str:
        """Generate a response given a prompt and optional tools."""
        pass

import os
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolCall

class MockProvider(LLMProvider):
    """Deterministic mock provider executing a fixed sequence of responses for tests."""

    def __init__(self, sequence: List[AIMessage] | None = None):
        self.sequence = sequence if sequence is not None else _MOCK_SEQUENCE
        self.call_count = 0
        self.history: List[str] = []

    def generate(self, prompt: str, system: str = "", tools: List[Dict[str, Any]] | None = None) -> AIMessage:
        self.history.append(prompt)

        if self.call_count < len(self.sequence):
            response = self.sequence[self.call_count]
            self.call_count += 1
            return response

        # Fallback if the test over-indexes the mock array
        self.call_count += 1
        return AIMessage(content="Mock generic response.")

class OpenAIProvider(LLMProvider):
    def __init__(self, model_name: str = "gpt-4o-mini"):
        from langchain_openai import ChatOpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key == "your_openai_api_key_here":
            raise ValueError("OPENAI_API_KEY environment variable is missing or invalid.")

        self.model = ChatOpenAI(model=model_name, api_key=api_key)

    def generate(self, prompt: str, system: str = "", tools: List[Any] | None = None) -> AIMessage:
        messages = []
        if system:
            messages.append(SystemMessage(content=system))
        messages.append(HumanMessage(content=prompt))

        if tools:
            model_with_tools = self.model.bind_tools(tools)
            return model_with_tools.invoke(messages)
        else:
            return self.model.invoke(messages)

# Global test sequence injection hook. Used by unittest.mock.patch in tests.
_MOCK_SEQUENCE: List[AIMessage] = []

def get_provider(provider_type: str = "mock", config: Dict[str, str] = None) -> LLMProvider:
    """Factory to retrieve configured LLM providers."""
    if provider_type == "mock":
        return MockProvider(sequence=_MOCK_SEQUENCE)
    elif provider_type == "openai":
        return OpenAIProvider()

    raise ValueError(f"Unsupported provider type: {provider_type}")
