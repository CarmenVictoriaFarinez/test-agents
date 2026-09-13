from __future__ import annotations
from datetime import datetime, date
from typing import Optional, Any


def parse_date_iso(value: Any) -> Optional[date]:
    """
    Acepta None, date o str 'YYYY-MM-DD'. Devuelve date o None si inválido.
    """
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def parse_amount(value: Any) -> Optional[float]:
    """
    Intenta convertir a float. Devuelve None si no es convertible o si es negativo.
    """
    if value is None:
        return None
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return None
    if amount < 0:
        return None
    return amount


def normalize_text(value: Any, max_len: int = 2000) -> Optional[str]:
    """
    Normaliza texto: strip, colapsa espacios, corta si excede max_len.
    Devuelve None si el texto queda vacío.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    text = " ".join(value.strip().split())
    if text == "":
        return None
    if len(text) > max_len:
        return text[:max_len]
    return text
