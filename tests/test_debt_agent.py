from agents.debt_agent import DebtAgent
from models import ConversationModel
from utils.idempotency import IdempotencyStore
from errors import CODE_NO_ACTION, CODE_DUPLICATE

class DummyParser:
    def __init__(self, parsed):
        self._parsed = parsed
    def parse_data(self, text):
        return dict(self._parsed)

def test_debt_agent_no_action_when_missing_fields():
    agent = DebtAgent()
    parser = DummyParser({"commitment_date": None, "committed_amount": None})
    result = agent.handle_turn(ConversationModel("nada"), parser)
    assert result.status == CODE_NO_ACTION

def test_debt_agent_builds_action_when_both_present():
    agent = DebtAgent()
    parser = DummyParser({"commitment_date": "2026-09-15", "committed_amount": 150.0, "extra_headers": {"X-Parser-Id": "abc"}})
    result = agent.handle_turn(ConversationModel("confirmo"), parser)
    assert result.status == "action_built"
    assert isinstance(result.action_request, dict)
    assert result.action_request["body"]["committed_amount"] == 150.0
    assert result.action_request["headers"]["x-parser-id"] == "abc"

def test_debt_agent_duplicate_ignored_with_shared_store():
    store = IdempotencyStore()
    agent1 = DebtAgent(idempotency_store=store)
    agent2 = DebtAgent(idempotency_store=store)
    parser = DummyParser({"commitment_date": "2026-09-15", "committed_amount": 150.0})
    r1 = agent1.handle_turn(ConversationModel("ok"), parser)
    assert r1.status == "action_built"
    r2 = agent2.handle_turn(ConversationModel("ok"), parser)
    assert r2.status == CODE_DUPLICATE
