from __future__ import annotations
from typing import Dict, Any, Optional
from datetime import date

from agents.base import BaseAgent
from integrations.contracts import Action
from errors import ValidationError
from utils.validators import parse_date_iso, parse_amount
from integrations.action import make_debt_action, HttpAction


class DebtAgent(BaseAgent):
    """
    Agent encargado de registrar compromisos de pago.
    Espera parsed dict con keys:
      - commitment_date: None | 'YYYY-MM-DD' | date
      - committed_amount: None | float | str
      - extra_headers: optional dict
    """
    success_response = "He registrado tu compromiso de pago correctamente."

    def _validate_and_normalize(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        commitment_raw = parsed.get("commitment_date")
        amount_raw = parsed.get("committed_amount")

        commitment_date: Optional[date] = parse_date_iso(commitment_raw)
        committed_amount: Optional[float] = parse_amount(amount_raw)

        # Si uno está presente y el otro no, es inválido para este agente
        if (commitment_date is None) ^ (committed_amount is None):
            raise ValidationError({"reason": "both_date_and_amount_required", "parsed": parsed})

        return {
            "commitment_date": commitment_date,
            "committed_amount": committed_amount,
            "extra_headers": self._normalize_extra_headers(parsed),
        }

    def _decide_action(self, normalized: Dict[str, Any], parser: Any) -> Optional[Action]:
        commitment_date = normalized.get("commitment_date")
        committed_amount = normalized.get("committed_amount")
        extra_headers = normalized.get("extra_headers", {})

        if commitment_date is None or committed_amount is None:
            return None

        # Construye la acción usando la fábrica; commitment_date es date, usamos isoformat()
        action: HttpAction = make_debt_action(commitment_date.isoformat(), committed_amount, extra_headers)
        return action
