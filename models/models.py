from __future__ import annotations

from typing import Any, Dict, Protocol


class ConversationModelProtocol(Protocol):
    def answer_user(self) -> str:
        ...


class ParserModelProtocol(Protocol):
    def parse_data(self, conversation: str) -> Dict[str, Any]:
        ...


class ConversationModel:
    """Modelo de conversación simulado para un turno de usuario."""

    def __init__(self, user_response: str) -> None:
        self._user_response = user_response

    def answer_user(self) -> str:
        return self._user_response


class ParserModel:
    """Parser simulado que devuelve datos estructurados preconfigurados."""

    def __init__(self, parsed_data: Dict[str, Any]) -> None:
        self._parsed_data = dict(parsed_data)

    def parse_data(self, conversation: str) -> Dict[str, Any]:
        return dict(self._parsed_data)