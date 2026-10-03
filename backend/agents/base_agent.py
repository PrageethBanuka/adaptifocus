"""Abstract base class for all AdaptiFocus agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, TypeVar

from pydantic import BaseModel

InputModel = TypeVar("InputModel", bound=BaseModel)
OutputModel = TypeVar("OutputModel", bound=BaseModel)


class BaseAgent(ABC, Generic[InputModel, OutputModel]):
    """Base interface for all agents in the AdaptiFocus system.

    Each agent:
    - Receives structured input data
    - Processes it according to its specialization
    - Returns a result dictionary

    This enables composability via the Coordinator agent.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable agent name."""
        ...

    @abstractmethod
    def analyze(self, data: InputModel | Dict[str, Any]) -> OutputModel:
        """Run the agent's analysis on the provided data.

        Args:
            data: Input dictionary — shape depends on the agent type.

        Returns:
            Validated result model with the agent's analysis output.
        """
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.name}>"
