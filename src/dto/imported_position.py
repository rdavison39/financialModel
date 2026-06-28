"""
imported_position.py

Defines the ImportedPosition DTO.

ImportedPosition is an immutable data transfer object produced by
brokerage importers.

It contains only factual information read directly from a brokerage
export.

Importers create these objects.

ImportService consumes them.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ImportedPosition:
    """
    Immutable investment position imported from a brokerage export.
    """

    #
    # Account Information
    #

    account_number: str

    #
    # Security Information
    #

    ticker: str

    company_name: str

    exchange: str

    currency: str

    asset_class: str

    #
    # Position Information
    #

    shares: Decimal

    average_cost: Decimal

    total_cost: Decimal

    market_price: Decimal

    market_value: Decimal

    unrealized_gain: Decimal

    annual_dividend: Decimal

    dividend_yield: Decimal