# ringr_agents/utils/idempotency.py
from __future__ import annotations
import hashlib
import json
from typing import Dict, Any, Set, Optional


def compute_action_id(url: str, payload: Dict[str, Any]) -> str:
    """
    Calcula un idempotency key estable a partir de url + payload.
    Usa JSON ordenado para garantizar determinismo.
    """
    payload_json = json.dumps(payload or {}, sort_keys=True, separators=(",", ":"))
    key = f"{url}|{payload_json}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


class IdempotencyStore:
    """
    Almacenamiento en memoria de action_ids. Interfaz simple:
      - exists(action_id) -> bool
      - add(action_id) -> None
    En producción podrías reemplazarlo por una DB.
    """

    def __init__(self, initial: Optional[Set[str]] = None) -> None:
        self._store: Set[str] = set(initial or set())

    def exists(self, action_id: str) -> bool:
        return action_id in self._store

    def add(self, action_id: str) -> None:
        self._store.add(action_id)

    def clear(self) -> None:
        self._store.clear()
