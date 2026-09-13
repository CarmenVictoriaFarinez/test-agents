# ringr_agents/integrations/action.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional

from utils.idempotency import compute_action_id
from integrations.contracts import Action

_SENSITIVE = {"authorization", "content-type"}
RINGR_BEARER_TOKEN = "ringr_test_token_9f3a2c1d"


def merge_headers_simple(
    base: Dict[str, str],
    parser_headers: Optional[Dict[str, str]],
    allow_override_sensitive: bool = False
) -> Dict[str, str]:
    """
    Mezcla base + parser_headers de forma segura:
      - normaliza claves a minúsculas
      - convierte claves/valores a str
      - por defecto evita que parser sobrescriba headers sensibles
    """
    result: Dict[str, str] = {k.lower(): str(v) for k, v in base.items()}

    if not parser_headers:
        return result

    for k, v in parser_headers.items():
        key = k.lower()
        val = str(v)
        if key in _SENSITIVE and not allow_override_sensitive:
            continue
        result[key] = val

    return result


@dataclass
class HttpResponse:
    status_code: int
    request: Dict[str, Any]


@dataclass
class HttpAction(Action):
    method: str
    url: str
    payload: Dict[str, Any]
    parser_headers: Optional[Dict[str, str]] = None
    allow_override_sensitive: bool = False
    simulated_status_code: int = 200

    def id(self) -> str:
        return compute_action_id(self.url, self.payload)

    def build_request(self) -> Dict[str, Any]:
        base = {"authorization": f"Bearer {RINGR_BEARER_TOKEN}", "content-type": "application/json"}
        headers = merge_headers_simple(base, self.parser_headers, allow_override_sensitive=self.allow_override_sensitive)
        return {"method": self.method, "url": self.url, "headers": headers, "body": self.payload}

    def execute(self) -> HttpResponse:
        """Simula un endpoint exitoso sin realizar ninguna llamada de red."""
        return HttpResponse(status_code=self.simulated_status_code, request=self.build_request())


def make_debt_action(commitment_date: str, committed_amount: float, extra_headers: Optional[Dict[str, str]] = None) -> HttpAction:
    url = "https://api.ringr.debt/v1/commitment"
    payload = {"commitment_date": commitment_date, "committed_amount": committed_amount}
    return HttpAction(method="POST", url=url, payload=payload, parser_headers=extra_headers)


def make_assistance_action(request_text: str, extra_headers: Optional[Dict[str, str]] = None) -> HttpAction:
    url = "https://api.ringr.assistance/v1/request"
    payload = {"request": request_text}
    return HttpAction(method="POST", url=url, payload=payload, parser_headers=extra_headers)
