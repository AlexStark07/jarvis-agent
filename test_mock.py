from jarvis.providers import get_provider, _MOCK_SEQUENCE
from langchain_core.messages import AIMessage

provider = get_provider("mock")
_MOCK_SEQUENCE.append(AIMessage(content="hello"))
print(provider.generate("test"))
