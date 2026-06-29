"""
imported_position.py

Defines the ImportedPosition data transfer object.

ImportedPosition is an immutable DTO representing a single investment
position imported directly from a brokerage export.

The field names intentionally mirror the terminology used by the
brokerage workbook. Translation into the application's canonical
database model is performed by ImportService.

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
    # Security Information
    #

    symbol: str

    description: str

    security_type: str

    currency: str

    #
    # Imported Values
    #

    quantity: Decimal

    unit_price: Decimal

    market_value: Decimal

    cost_basis: Decimal