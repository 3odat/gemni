from abc import ABC, abstractmethod
from typing import Any, Dict

from core.logger import logger


class BaseAgent(ABC):
    """
    Base class for all agents in the system.
    """

    name: str = "base"

    @abstractmethod
    async def run(self, *args: Any, **kwargs: Any) -> Any:
        """
        Main async entrypoint for agent behavior.
        """
        raise NotImplementedError

    async def log(self, message: str, **context: Dict[str, Any]) -> None:
        prefix = f"[{self.name}]"
        if context:
            logger.info(f"{prefix} {message} | ctx={context}")
        else:
            logger.info(f"{prefix} {message}")
