"""
imported_cash.py

Defines the ImportedCash data transfer object.

ImportedCash is an immutable DTO representing a single cash balance
reported by a brokerage export.

Importers create these objects.

ImportService consumes them.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ImportedCash:
    """
    Immutable cash balance imported from a brokerage export.
    """

    currency: str

    amount: Decimal