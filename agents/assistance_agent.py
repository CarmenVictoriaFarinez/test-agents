# ringr_agents/agents/assistance_agent.py
from __future__ import annotations
from typing import Dict, Any, Optional

from agents.base import BaseAgent
from integrations.contracts import Action
from utils.validators import normalize_text
from integrations.action import make_assistance_action, HttpAction


class AssistanceAgent(BaseAgent):
    """
    Agent encargado de registrar solicitudes de atención.
    Espera parsed dict con keys:
      - request: None | str
      - extra_headers: optional dict
    """
    success_response = "He registrado tu solicitud para que la gestione nuestro equipo."

    def _validate_and_normalize(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        request_raw = parsed.get("request")
        request_text = normalize_text(request_raw, max_len=2000)

        # If request is None or empty -> no action
        if request_text is None:
            return {"request": None, "extra_headers": self._normalize_extra_headers(parsed)}

        return {"request": request_text, "extra_headers": self._normalize_extra_headers(parsed)}

    def _decide_action(self, normalized: Dict[str, Any], parser: Any) -> Optional[Action]:
        request_text = normalized.get("request")
        extra_headers = normalized.get("extra_headers", {})

        if not request_text:
            return None

        action: HttpAction = make_assistance_action(request_text, extra_headers)
        return action
