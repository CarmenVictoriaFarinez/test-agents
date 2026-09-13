# ringr_agents/errors.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict

# Mensajes reutilizables
MSG_CONVERSATION_ERROR = "Error obtaining user response from ConversationModel"
MSG_PARSER_ERROR = "Error parsing conversation data"
MSG_VALIDATION_ERROR = "Validation or normalization failed"
MSG_ACTION_ID_ERROR = "Failed to compute action id"
MSG_BUILD_REQUEST_ERROR = "Failed to build action request"
MSG_ACTION_FAILED = "External action returned an error status"
MSG_DUPLICATE_ACTION = "Action already processed; duplicate ignored"
MSG_NO_ACTION = "No action required for this turn"

# Códigos de error (útiles para tests y logs)
CODE_CONVERSATION_ERROR = "conversation_error"
CODE_PARSER_ERROR = "parser_error"
CODE_VALIDATION_ERROR = "validation_error"
CODE_ACTION_ID_ERROR = "action_id_error"
CODE_BUILD_REQUEST_ERROR = "build_request_error"
CODE_ACTION_FAILED = "action_failed"
CODE_DUPLICATE = "duplicate_ignored"
CODE_NO_ACTION = "no_action"

@dataclass
class AgentError(Exception):
    """Excepción base para errores controlados en agentes."""
    code: str
    message: str
    details: Dict[str, Any] | None = None

    def __str__(self) -> str:
        base = f"{self.code}: {self.message}"
        if self.details:
            return f"{base} | details={self.details}"
        return base

class ConversationError(AgentError):
    def __init__(self, details: Dict[str, Any] | None = None):
        super().__init__(CODE_CONVERSATION_ERROR, MSG_CONVERSATION_ERROR, details)

class ParserError(AgentError):
    def __init__(self, details: Dict[str, Any] | None = None):
        super().__init__(CODE_PARSER_ERROR, MSG_PARSER_ERROR, details)

class ValidationError(AgentError):
    def __init__(self, details: Dict[str, Any] | None = None):
        super().__init__(CODE_VALIDATION_ERROR, MSG_VALIDATION_ERROR, details)

class ActionIdError(AgentError):
    def __init__(self, details: Dict[str, Any] | None = None):
        super().__init__(CODE_ACTION_ID_ERROR, MSG_ACTION_ID_ERROR, details)

class BuildRequestError(AgentError):
    def __init__(self, details: Dict[str, Any] | None = None):
        super().__init__(CODE_BUILD_REQUEST_ERROR, MSG_BUILD_REQUEST_ERROR, details)


class ActionFailedError(AgentError):
    def __init__(self, details: Dict[str, Any] | None = None):
        super().__init__(CODE_ACTION_FAILED, MSG_ACTION_FAILED, details)
