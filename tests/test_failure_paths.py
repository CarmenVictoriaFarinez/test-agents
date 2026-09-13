import pytest

from agents.assistance_agent import AssistanceAgent
from agents.base import BaseAgent
from errors import (
    CODE_ACTION_ID_ERROR,
    CODE_BUILD_REQUEST_ERROR,
    CODE_CONVERSATION_ERROR,
    CODE_PARSER_ERROR,
    CODE_VALIDATION_ERROR,
    AgentError,
    ActionIdError,
    ActionFailedError,
    BuildRequestError,
    ConversationError,
    ParserError,
    ValidationError,
)
from integrations.action import HttpAction, merge_headers_simple
from integrations.contracts import Action
from models import ConversationModel, ParserModel
from utils.idempotency import IdempotencyStore
from utils.validators import normalize_text, parse_amount, parse_date_iso


class BrokenConversation:
    def answer_user(self):
        raise RuntimeError("conversation unavailable")


class WrongTypeConversation:
    def answer_user(self):
        return 123


class BrokenParser:
    def parse_data(self, conversation):
        raise RuntimeError("parser unavailable")


class ConfigurableAgent(BaseAgent):
    def __init__(self, mode):
        super().__init__()
        self.mode = mode

    def _validate_and_normalize(self, parsed):
        if self.mode == "validation_error":
            raise RuntimeError("normalization failed")
        return parsed

    def _decide_action(self, normalized, parser):
        if self.mode == "decision_error":
            raise RuntimeError("decision failed")
        return ExplodingAction(self.mode) if self.mode != "no_action" else None


class ExplodingAction(Action):
    def __init__(self, mode):
        self.mode = mode

    def id(self):
        if self.mode == "id_error":
            raise RuntimeError("id failed")
        return "test-action"

    def build_request(self):
        if self.mode == "build_error":
            raise RuntimeError("build failed")
        return {"method": "POST"}

    def execute(self):
        if self.mode == "execute_error":
            raise RuntimeError("execute failed")
        return type("Response", (), {"status_code": 200})()


def test_conversation_errors_are_controlled():
    agent = AssistanceAgent()

    failed = agent.handle_turn(BrokenConversation(), ParserModel({"request": "help"}))
    wrong_type = agent.handle_turn(WrongTypeConversation(), ParserModel({"request": "help"}))

    assert failed.status == CODE_CONVERSATION_ERROR
    assert wrong_type.status == CODE_CONVERSATION_ERROR
    assert failed.agent_response
    assert wrong_type.agent_response


def test_parser_exception_is_controlled():
    result = AssistanceAgent().handle_turn(ConversationModel("help"), BrokenParser())

    assert result.status == CODE_PARSER_ERROR
    assert result.agent_response


@pytest.mark.parametrize(
    "mode, expected_status",
    [
        ("validation_error", CODE_VALIDATION_ERROR),
        ("decision_error", CODE_VALIDATION_ERROR),
        ("id_error", CODE_ACTION_ID_ERROR),
        ("build_error", CODE_BUILD_REQUEST_ERROR),
        ("execute_error", CODE_BUILD_REQUEST_ERROR),
    ],
)
def test_internal_turn_failures_are_controlled(mode, expected_status):
    result = ConfigurableAgent(mode).handle_turn(
        ConversationModel("input"), ParserModel({"value": "data"})
    )

    assert result.status == expected_status
    assert result.action_request is None
    assert result.agent_response


def test_headers_can_override_sensitive_values_explicitly():
    result = merge_headers_simple(
        {"Authorization": "Bearer default", "Content-Type": "application/json"},
        {"Authorization": "Bearer custom", "Content-Type": "text/plain"},
        allow_override_sensitive=True,
    )

    assert result == {
        "authorization": "Bearer custom",
        "content-type": "text/plain",
    }


def test_http_action_can_simulate_failure_and_preserves_request():
    action = HttpAction(
        method="POST",
        url="https://api.example/failure",
        payload={"value": 1},
        simulated_status_code=500,
    )

    response = action.execute()

    assert response.status_code == 500
    assert response.request["body"] == {"value": 1}


def test_debt_rejects_invalid_date_with_amount():
    from agents.debt_agent import DebtAgent

    result = DebtAgent().handle_turn(
        ConversationModel("payment"),
        ParserModel({"commitment_date": "invalid", "committed_amount": 10}),
    )

    assert result.status == CODE_VALIDATION_ERROR


def test_assistance_normalizes_non_string_and_blank_requests():
    agent = AssistanceAgent()

    numeric = agent.handle_turn(ConversationModel("help"), ParserModel({"request": 123}))
    blank = agent.handle_turn(ConversationModel("help"), ParserModel({"request": "   "}))

    assert numeric.status == "action_built"
    assert numeric.action_request["body"]["request"] == "123"
    assert blank.status == "no_action"


def test_validators_cover_supported_and_invalid_types():
    assert parse_date_iso(None) is None
    assert parse_date_iso(123) is None
    assert parse_amount(None) is None
    assert parse_amount(object()) is None
    assert normalize_text(None) is None
    assert normalize_text(123) == "123"


def test_idempotency_store_can_be_cleared():
    store = IdempotencyStore({"action-1"})
    assert store.exists("action-1")
    store.clear()
    assert not store.exists("action-1")


def test_error_objects_expose_messages_and_details():
    errors = [
        ConversationError({"source": "conversation"}),
        ParserError({"source": "parser"}),
        ValidationError({"source": "validation"}),
        ActionIdError({"source": "id"}),
        BuildRequestError({"source": "request"}),
        ActionFailedError({"status_code": 503}),
    ]

    for error in errors:
        assert error.code
        assert error.message
        assert error.details
        assert error.code in str(error)


def test_success_result_uses_agent_default_message():
    result = ConfigurableAgent("success").handle_turn(
        ConversationModel("input"), ParserModel({"value": "data"})
    )

    assert result.status == "action_built"
    assert result.agent_response == "La acción se ha procesado correctamente."
