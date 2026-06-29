"""
imported_position.py

Data Transfer Object (DTO) representing a security position imported
from a brokerage statement.

This object is produced by an importer and later consumed by the
ImportService to persist the data to the database.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ImportedPosition:
    """
    Represents a single investment position imported from a brokerage
    statement.

    Attributes
    ----------
    symbol
        Trading symbol (ticker).

    description
        Security description.

    quantity
        Number of shares or units held.

    unit_price
        Market price per share/unit.

    market_value
        Total current market value.

    cost_basis
        Total cost basis (book value / ACB).

    currency
        ISO currency code (e.g. "CAD", "USD").

    security_type
        Optional security classification
        (Stock, ETF, Mutual Fund, GIC, etc.).
    """

    symbol: str
    description: str
    quantity: Decimal
    unit_price: Decimal
    market_value: Decimal
    cost_basis: Decimal
    currency: str
    security_type: str = ""