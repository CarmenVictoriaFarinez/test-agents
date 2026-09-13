from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class Action(ABC):
    """Contrato común para cualquier acción externa del sistema."""

    @abstractmethod
    def id(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def build_request(self) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def execute(self) -> Any:
        raise NotImplementedError
