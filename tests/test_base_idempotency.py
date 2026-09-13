from utils.idempotency import IdempotencyStore
from agents.debt_agent import DebtAgent
from agents.assistance_agent import AssistanceAgent
from models import ConversationModel

class DummyParser:
    def __init__(self, parsed): self._parsed = parsed
    def parse_data(self, text): return dict(self._parsed)

def test_shared_idempotency_across_agents():
    store = IdempotencyStore()
    d = DebtAgent(idempotency_store=store)
    a = AssistanceAgent(idempotency_store=store)
    # Use different payloads so ids differ
    pd = DummyParser({"commitment_date": "2026-09-15", "committed_amount": 100.0})
    pa = DummyParser({"request": "help me"})
    rd = d.handle_turn(ConversationModel("ok"), pd)
    ra = a.handle_turn(ConversationModel("ok"), pa)
    assert rd.status == "action_built"
    assert ra.status == "action_built"
    # Re-run same debt action -> duplicate
    rd2 = d.handle_turn(ConversationModel("ok"), pd)
    assert rd2.status != "action_built"
