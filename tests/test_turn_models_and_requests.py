import logging

from agents.assistance_agent import AssistanceAgent
from agents.debt_agent import DebtAgent
from integrations.action import HttpAction
from models import ConversationModel, ParserModel
from errors import CODE_ACTION_FAILED, CODE_DUPLICATE, CODE_PARSER_ERROR, CODE_VALIDATION_ERROR

def test_debt_turn_uses_models_and_builds_post_request():
    conversation = ConversationModel("Confirmo el pago")
    parser = ParserModel(
        {
            "commitment_date": "2026-09-15",
            "committed_amount": 150.0,
            "extra_headers": {"X-Parser-Trace": "debt-1"},
        }
    )

    result = DebtAgent().handle_turn(conversation, parser)

    assert result.status == "action_succeeded"
    assert result.response_status_code == 200
    assert result.agent_response == "He registrado tu compromiso de pago correctamente."
    assert result.action_request == {
        "method": "POST",
        "url": "https://api.ringr.debt/v1/commitment",
        "headers": {
            "authorization": "Bearer ringr_test_token_9f3a2c1d",
            "content-type": "application/json",
            "x-parser-trace": "debt-1",
        },
        "body": {
            "commitment_date": "2026-09-15",
            "committed_amount": 150.0,
        },
    }


def test_assistance_turn_builds_request_without_real_http_call():
    result = AssistanceAgent().handle_turn(
        ConversationModel("Necesito ayuda"),
        ParserModel({"request": "Necesito ayuda", "extra_headers": {"X-Queue": "human"}}),
    )

    assert result.status == "action_succeeded"
    assert result.response_status_code == 200
    assert result.agent_response == "He registrado tu solicitud para que la gestione nuestro equipo."
    assert result.action_request["method"] == "POST"
    assert result.action_request["url"] == "https://api.ringr.assistance/v1/request"
    assert result.action_request["body"] == {"request": "Necesito ayuda"}
    assert result.action_request["headers"]["authorization"] == "Bearer ringr_test_token_9f3a2c1d"
    assert result.action_request["headers"]["x-queue"] == "human"


def test_parser_must_return_a_dict():
    class InvalidParser:
        def parse_data(self, conversation):
            return ["not", "json"]

    result = AssistanceAgent().handle_turn(ConversationModel("Hola"), InvalidParser())

    assert result.status == CODE_PARSER_ERROR


def test_invalid_extra_headers_prevent_action():
    result = DebtAgent().handle_turn(
        ConversationModel("Confirmo"),
        ParserModel(
            {
                "commitment_date": "2026-09-15",
                "committed_amount": 150.0,
                "extra_headers": "Authorization: invalid",
            }
        ),
    )

    assert result.status == CODE_VALIDATION_ERROR
    assert result.action_request is None


def test_same_action_is_not_built_twice():
    agent = AssistanceAgent()
    conversation = ConversationModel("Ayuda")
    parser = ParserModel({"request": "Ayuda"})

    first = agent.handle_turn(conversation, parser)
    second = agent.handle_turn(conversation, parser)

    assert first.status == "action_succeeded"
    assert second.status == CODE_DUPLICATE
    assert second.action_request is None
    assert second.agent_response == "Esta acción ya había sido procesada."


def test_failed_external_response_is_reported_and_not_marked_idempotent():
    class FailingAssistanceAgent(AssistanceAgent):
        def _decide_action(self, normalized, parser):
            return HttpAction(
                method="POST",
                url="https://api.ringr.assistance/v1/request",
                payload={"request": normalized["request"]},
                simulated_status_code=503,
            )

    agent = FailingAssistanceAgent()
    result = agent.handle_turn(
        ConversationModel("Ayuda"), ParserModel({"request": "Ayuda"})
    )

    assert result.status == CODE_ACTION_FAILED
    assert result.response_status_code == 503
    assert result.agent_response == "La solicitud externa no pudo completarse."


def test_no_action_generates_a_conversational_response():
    result = AssistanceAgent().handle_turn(
        ConversationModel("Hola"), ParserModel({"request": None})
    )

    assert result.status == "no_action"
    assert result.agent_response == "No hay información suficiente para ejecutar una acción."


def test_turn_writes_safe_lifecycle_logs(caplog):
    caplog.set_level(logging.INFO, logger="agents.base")

    AssistanceAgent().handle_turn(
        ConversationModel("Ayuda"), ParserModel({"request": "Ayuda"})
    )

    messages = [record.getMessage() for record in caplog.records]
    assert any("agent_turn_started" in message for message in messages)
    assert any("action_succeeded" in message for message in messages)
    assert all("ringr_test_token" not in message for message in messages)
