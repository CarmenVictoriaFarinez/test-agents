from agents.assistance_agent import AssistanceAgent
from models import ConversationModel
from utils.idempotency import IdempotencyStore
from errors import CODE_NO_ACTION, CODE_DUPLICATE

class DummyParser:
    def __init__(self, parsed):
        self._parsed = parsed
    def parse_data(self, text):
        return dict(self._parsed)

def test_assistance_no_action_when_no_request():
    agent = AssistanceAgent()
    parser = DummyParser({"request": None})
    result = agent.handle_turn(ConversationModel("nada"), parser)
    assert result.status == CODE_NO_ACTION

def test_assistance_builds_action_when_request_present():
    agent = AssistanceAgent()
    parser = DummyParser({"request": "I need help", "extra_headers": {"X-Parser-Id": "xyz"}})
    result = agent.handle_turn(ConversationModel("help"), parser)
    assert result.status == "action_built"
    assert result.action_request["body"]["request"] == "I need help"
    assert result.action_request["headers"]["x-parser-id"] == "xyz"

def test_assistance_duplicate_ignored_shared_store():
    store = IdempotencyStore()
    a1 = AssistanceAgent(idempotency_store=store)
    a2 = AssistanceAgent(idempotency_store=store)
    parser = DummyParser({"request": "I need help"})
    r1 = a1.handle_turn(ConversationModel("help"), parser)
    assert r1.status == "action_built"
    r2 = a2.handle_turn(ConversationModel("help"), parser)
    assert r2.status == CODE_DUPLICATE
