from abc import ABC, abstractmethod
from typing import Any, Dict, List
from pydantic import BaseModel, Field

from jarvis.providers import LLMProvider
from jarvis.workers import WorkerManager

class AgentInput(BaseModel):
    task_id: str
    description: str
    context: Dict[str, Any] = Field(default_factory=dict)

class AgentOutput(BaseModel):
    task_id: str
    status: str
    result: str
    error: str | None = None
    requires_approval: bool = False
    pending_action: Dict[str, Any] | None = None

class Agent(ABC):
    """Abstract interface defining the contract for all specialist agents."""

    def __init__(self, provider: LLMProvider, worker_manager: WorkerManager | None = None, execution_service: Any | None = None):
        self.provider = provider
        self.worker_manager = worker_manager
        self.execution_service = execution_service

    @property
    @abstractmethod
    def agent_id(self) -> str:
        """Stable agent identifier."""
        pass

    @property
    @abstractmethod
    def allowed_tools(self) -> List[str]:
        """List of tool names this agent is authorized to use."""
        pass

    @abstractmethod
    def execute(self, inputs: AgentInput) -> AgentOutput:
        """Execute the agent's specific workflow."""
        pass
