import json
from integrations.action import HttpAction, make_debt_action, merge_headers_simple
from utils.idempotency import compute_action_id

def test_compute_action_id_stable():
    url = "https://api.example/v1/x"
    payload = {"a": 1, "b": 2}
    id1 = compute_action_id(url, payload)
    id2 = compute_action_id(url, {"b":2, "a":1})
    assert id1 == id2

def test_httpaction_build_request_and_headers():
    action = make_debt_action("2026-09-15", 150.0, extra_headers={"X-Parser-Id": "abc", "Authorization": "mal"})
    req = action.build_request()
    assert req["method"] == "POST"
    assert req["url"].startswith("https://api.ringr.debt")
    # headers normalized to lowercase
    headers = req["headers"]
    assert headers["x-parser-id"] == "abc"
    # authorization should remain the default (not overwritten)
    assert "authorization" in headers
    assert headers["authorization"].startswith("Bearer ")

def test_merge_headers_simple_respects_sensitive():
    base = {"Authorization": "Bearer good", "Content-Type": "application/json", "X-A": "1"}
    parser = {"X-A": "2", "Authorization": "Bearer bad"}
    out = merge_headers_simple(base, parser)
    assert out["x-a"] == "2"
    assert out["authorization"] == "Bearer good"
