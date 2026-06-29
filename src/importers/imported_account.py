"""
imported_account.py

Data Transfer Object (DTO) representing an account imported from a
brokerage statement.

This object is produced by an importer and later consumed by the
ImportService to persist the data to the database.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from src.importers.imported_cash import ImportedCash
from src.importers.imported_position import ImportedPosition


@dataclass(slots=True)
class ImportedAccount:
    """
    Represents a brokerage account imported from a statement.

    Attributes
    ----------
    account_number
        Brokerage account number.

    account_name
        Display name of the account.

    account_type
        Type of account (RRSP, TFSA, Cash, Margin, etc.).

    statement_date
        Statement date.

    cash
        Imported cash balances.

    positions
        Imported investment positions.
    """

    account_number: str
    account_name: str
    account_type: str
    statement_date: date

    cash: list[ImportedCash] = field(default_factory=list)
    positions: list[ImportedPosition] = field(default_factory=list)