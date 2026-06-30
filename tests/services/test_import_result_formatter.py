"""
Unit tests for import_result_formatter.py.
"""

from __future__ import annotations

from src.services.import_result import ImportResult
from src.services.import_result_formatter import format_import_result


def test_format_import_result_contains_summary_counts() -> None:
    """
    ImportResult formatting includes the important import counts.
    """

    result = ImportResult(
        success=True,
        import_id=12,
        accounts_imported=1,
        positions_imported=10,
        cash_balances_imported=2,
    )

    formatted = format_import_result(result)

    assert "Success: True" in formatted
    assert "Import ID: 12" in formatted
    assert "Accounts imported: 1" in formatted
    assert "Positions imported: 10" in formatted
    assert "Cash balances imported: 2" in formatted
