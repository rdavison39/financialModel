from decimal import Decimal

from src.gui.treeview_sort import numeric_sort_key, parse_number, parse_text


def test_parse_number_handles_currency_and_percent() -> None:
    assert parse_number("$1,234.50") == Decimal("1234.50")
    assert parse_number("-12.5%") == Decimal("-12.5")
    assert parse_number("--") is None


def test_numeric_sort_key_uses_decimal() -> None:
    assert numeric_sort_key("$100.00") > numeric_sort_key("$9.00")


def test_parse_text_is_case_insensitive() -> None:
    assert parse_text("  Bank of Montreal ") == "bank of montreal"
