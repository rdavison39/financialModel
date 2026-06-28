"""
imported_position.py

Defines the ImportedPosition data transfer object (DTO).

This object represents a single security imported from a brokerage
export file. It is intentionally independent of the database and is
used to move data from the importer to the validation and persistence
layers.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass(slots=True)
class ImportedPosition:
    """
    Represents one imported security from a brokerage export.
    """

    #
    # Account Information
    #

    account_number: str
    account_name: str
    owner: str
    brokerage: str

    #
    # Security Information
    #

    ticker: str
    company_name: str
    currency: str

    #
    # Position
    #

    shares: Decimal
    average_cost: Decimal
    book_cost: Decimal

    #
    # Imported Market Information
    #
    # These values come directly from the brokerage export.
    # They are NOT considered authoritative long-term.
    #

    market_price: Decimal
    market_value: Decimal
    unrealized_gain: Decimal

    #
    # Optional Information
    #

    sector: Optional[str] = None
    industry: Optional[str] = None
    exchange: Optional[str] = None
    country: Optional[str] = None

    def __str__(self) -> str:
        """
        Human-readable representation.
        """

        return (
            f"{self.account_name}: "
            f"{self.ticker} "
            f"({self.shares} shares)"
        )