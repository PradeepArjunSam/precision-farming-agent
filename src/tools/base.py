from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseTool(ABC):
    @abstractmethod
    def run(self, input_data: Any) -> Dict[str, Any]:
        """
        Execute the tool logic.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Return the name of the tool.
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """
        Return a description of what the tool does.
        """
        pass
