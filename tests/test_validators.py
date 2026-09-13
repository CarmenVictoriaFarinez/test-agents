from datetime import date
import pytest
from utils.validators import parse_date_iso, parse_amount, normalize_text

def test_parse_date_iso_valid():
    d = parse_date_iso("2026-09-15")
    assert isinstance(d, date)
    assert d.isoformat() == "2026-09-15"

def test_parse_date_iso_invalid():
    assert parse_date_iso("15-09-2026") is None
    assert parse_date_iso("not-a-date") is None
    assert parse_date_iso(None) is None

def test_parse_amount_valid():
    assert parse_amount("150") == 150.0
    assert parse_amount(12.5) == 12.5

def test_parse_amount_invalid():
    assert parse_amount("abc") is None
    assert parse_amount(-5) is None
    assert parse_amount(None) is None

def test_normalize_text():
    assert normalize_text("  hola   mundo  ") == "hola mundo"
    assert normalize_text("") is None
    assert normalize_text(None) is None
    long_text = "x" * 3000
    assert len(normalize_text(long_text, max_len=1000)) == 1000
