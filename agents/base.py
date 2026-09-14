from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any

from errors import (
    ConversationError,
    ParserError,
    ValidationError,
    ActionIdError,
    BuildRequestError,
    ActionFailedError,
    CODE_NO_ACTION,
    CODE_DUPLICATE,
    CODE_ACTION_FAILED,
    CODE_CONVERSATION_ERROR,
    CODE_PARSER_ERROR,
    CODE_VALIDATION_ERROR,
)
from utils.idempotency import IdempotencyStore
from models import ConversationModelProtocol, ParserModelProtocol
from integrations.contracts import Action

logger = logging.getLogger(__name__)

@dataclass
class AgentResult:
    action_request: Optional[Dict[str, Any]]
    status: str
    details: Optional[Dict[str, Any]] = None
    response_status_code: Optional[int] = None
    agent_response: str = ""


class BaseAgent(ABC):
    success_response = "La acción se ha procesado correctamente."

    def __init__(self, idempotency_store: Optional[IdempotencyStore] = None) -> None:
        self._idempotency = idempotency_store or IdempotencyStore()

    def _extract_user_text(self, conversation: ConversationModelProtocol) -> str:
        try:
            user_text = conversation.answer_user()
            if not isinstance(user_text, str):
                raise TypeError("ConversationModel.answer_user() must return a str")
            return user_text
        except Exception as exc:
            raise ConversationError({"error": str(exc)})

    def _normalize_extra_headers(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        headers = parsed.get("extra_headers", {})
        if headers is None:
            return {}
        if not isinstance(headers, dict):
            raise ValidationError({"reason": "extra_headers_must_be_dict"})
        return dict(headers)

    def _result(
        self,
        status: str,
        action_request: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None,
        response_status_code: Optional[int] = None,
    ) -> AgentResult:
        messages = {
            CODE_NO_ACTION: "No hay información suficiente para ejecutar una acción.",
            CODE_DUPLICATE: "Esta acción ya había sido procesada.",
            CODE_CONVERSATION_ERROR: "No pude obtener correctamente tu respuesta.",
            CODE_PARSER_ERROR: "No pude interpretar la información de la conversación.",
            CODE_VALIDATION_ERROR: "La información recibida no es válida para esta operación.",
            "action_id_error": "No pude identificar la acción de forma segura.",
            "build_request_error": "No pude preparar la solicitud externa.",
            CODE_ACTION_FAILED: "La solicitud externa no pudo completarse.",
        }
        return AgentResult(
            action_request,
            status,
            details,
            response_status_code,
            messages.get(status, self.success_response),
        )

    def handle_turn(
        self,
        conversation: ConversationModelProtocol,
        parser: ParserModelProtocol,
    ) -> AgentResult:
        logger.info("agent_turn_started agent=%s", type(self).__name__)
        # 1. Obtener texto del ConversationModel
        try:
            user_text = self._extract_user_text(conversation)
        except ConversationError as err:
            logger.warning("conversation_error agent=%s", type(self).__name__)
            return self._result(err.code, details={"message": err.message, "details": err.details})

        # 2. Parsear
        try:
            parsed = parser.parse_data(user_text)
            if not isinstance(parsed, dict):
                raise TypeError("ParserModel.parse_data() must return a dict")
        except Exception as exc:
            err = ParserError({"error": str(exc)})
            logger.warning("parser_error agent=%s", type(self).__name__)
            return self._result(err.code, details={"message": err.message, "details": err.details})

        # 3. Validar y normalizar
        try:
            normalized = self._validate_and_normalize(parsed)
        except Exception as exc:
            if hasattr(exc, "code") and hasattr(exc, "message"):
                logger.warning("validation_error agent=%s", type(self).__name__)
                return self._result(exc.code, details={"message": exc.message, "details": getattr(exc, "details", None)})
            err = ValidationError({"error": str(exc)})
            logger.warning("validation_error agent=%s", type(self).__name__)
            return self._result(err.code, details={"message": err.message, "details": err.details})

        # 4. Decidir acción
        try:
            action = self._decide_action(normalized, parser)
        except Exception as exc:
            if hasattr(exc, "code") and hasattr(exc, "message"):
                logger.warning("decision_error agent=%s", type(self).__name__)
                return self._result(exc.code, details={"message": exc.message, "details": getattr(exc, "details", None)})
            err = ValidationError({"error": str(exc)})
            logger.warning("decision_error agent=%s", type(self).__name__)
            return self._result(err.code, details={"message": err.message, "details": err.details})

        if action is None:
            logger.info("no_action agent=%s", type(self).__name__)
            return self._result(CODE_NO_ACTION)

        # 5. Idempotencia y construcción de request
        try:
            action_id = action.id()
        except Exception as exc:
            err = ActionIdError({"error": str(exc)})
            logger.exception("action_id_error agent=%s", type(self).__name__)
            return self._result(err.code, details={"message": err.message, "details": err.details})

        if self._idempotency.exists(action_id):
            logger.info("duplicate_action agent=%s", type(self).__name__)
            return self._result(CODE_DUPLICATE, details={"action_id": action_id})

        try:
            request = action.build_request()
        except Exception as exc:
            err = BuildRequestError({"error": str(exc)})
            logger.exception("build_request_error agent=%s", type(self).__name__)
            return self._result(err.code, details={"message": err.message, "details": err.details})

        try:
            response = action.execute()
        except Exception as exc:
            err = BuildRequestError({"error": str(exc)})
            logger.exception("action_execution_error agent=%s", type(self).__name__)
            return self._result(err.code, details={"message": err.message, "details": err.details})

        if response.status_code >= 400:
            err = ActionFailedError({"status_code": response.status_code})
            logger.error("action_failed agent=%s status_code=%s", type(self).__name__, response.status_code)
            return self._result(
                CODE_ACTION_FAILED,
                action_request=request,
                details={"message": err.message, "details": err.details},
                response_status_code=response.status_code,
            )

        self._idempotency.add(action_id)
        logger.info("action_succeeded agent=%s status_code=%s", type(self).__name__, response.status_code)
        return self._result(
            "action_succeeded",
            action_request=request,
            details={"action_id": action_id},
            response_status_code=response.status_code,
        )

    @abstractmethod
    def _validate_and_normalize(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def _decide_action(self, normalized: Dict[str, Any], parser: Any) -> Optional[Action]:
        raise NotImplementedError
