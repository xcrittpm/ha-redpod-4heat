"""Tests for the protocol parser (no Home Assistant needed).

Run with:  python -m pytest tests
"""

import importlib.util
import pathlib
import sys

# Load api.py on its own so the tests do not need Home Assistant installed.
_API = pathlib.Path(__file__).parents[1] / "custom_components" / "redpod_4heat" / "api.py"
_spec = importlib.util.spec_from_file_location("fourheat_api", _API)
api = importlib.util.module_from_spec(_spec)
sys.modules["fourheat_api"] = api
_spec.loader.exec_module(api)

# A real answer from a Red-Pod stove (P0147) with a 4Heat module.
SAMPLE = (
    '["SEL","22","J30001000000000007","J30002000000000000","J30005000000000022",'
    '"J30006000000000020","B20364000000000006","B20575000000000001",'
    '"J30011000000-00001","J20119000000002100","J30138000000000040"]'
)


def test_parse_response():
    items = api.parse_response(SAMPLE)
    assert items[0] == "SEL"
    assert items[2] == "J30001000000000007"


def test_parse_item_read_only():
    code, reading = api.parse_item("J30005000000000022")
    assert code == "30005"
    assert reading.value == 22
    assert not reading.writable


def test_parse_item_writable():
    code, reading = api.parse_item("B20364000000000006")
    assert code == "20364"
    assert reading.value == 6
    assert reading.writable


def test_parse_item_negative():
    code, reading = api.parse_item("J30011000000-00001")
    assert code == "30011"
    assert reading.value == -1


def test_parse_item_rejects_garbage():
    assert api.parse_item("SEL") is None
    assert api.parse_item("Xabcde000000000001") is None
    assert api.parse_item("J30001000000abc001") is None
