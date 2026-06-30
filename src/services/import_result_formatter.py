"""
import_result_formatter.py

Formatting helpers for displaying ImportResult objects.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from src.services.import_result import ImportResult


def format_import_result(
    result: ImportResult,
) -> str:
    """
    Format an ImportResult as plain text.
    """

    lines = [
        "Import complete.",
        f"Success: {result.success}",
        f"Import ID: {result.import_id}",
        f"Accounts imported: {result.accounts_imported}",
        f"Positions imported: {result.positions_imported}",
        f"Cash balances imported: {result.cash_balances_imported}",
        f"Brokerages created: {result.brokerages_created}",
        f"Accounts created: {result.accounts_created}",
        f"Companies created: {result.companies_created}",
    ]

    if result.warnings:
        lines.append("")
        lines.append("Warnings:")
        lines.extend(result.warnings)

    if result.errors:
        lines.append("")
        lines.append("Errors:")
        lines.extend(result.errors)

    return "\n".join(lines)
