"""
imported_cash.py

Data Transfer Object (DTO) representing a cash balance imported from
a brokerage statement.

This object is produced by an importer and later consumed by the
ImportService to persist the data to the database.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ImportedCash:
    """
    Represents a single cash balance imported from a brokerage statement.

    Attributes
    ----------
    currency
        ISO currency code (e.g. "CAD", "USD").

    amount
        Cash balance in the specified currency.
    """

    currency: str
    amount: Decimal