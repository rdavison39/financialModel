"""
imported_account.py

Defines the ImportedAccount data transfer object.

ImportedAccount represents a single brokerage account imported from an
export file. It contains only factual information read directly from
the workbook along with the imported positions and cash balances
belonging to the account.

Importers create these objects.

ImportService consumes them.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import date

from src.dto.imported_cash import ImportedCash
from src.dto.imported_position import ImportedPosition


@dataclass(slots=True)
class ImportedAccount:
    """
    Represents one imported brokerage account.
    """

    #
    # Imported Account Information
    #

    account_number: str

    account_name: str

    account_type: str

    statement_date: date

    #
    # Imported Data
    #

    positions: list[ImportedPosition] = field(
        default_factory=list
    )

    cash: list[ImportedCash] = field(
        default_factory=list
    )

    @property
    def number_of_positions(self) -> int:
        """
        Returns the number of imported positions.
        """
        return len(self.positions)

    @property
    def number_of_cash_balances(self) -> int:
        """
        Returns the number of imported cash balances.
        """
        return len(self.cash)

    def add_position(
        self,
        position: ImportedPosition,
    ) -> None:
        """
        Adds an imported position.
        """
        self.positions.append(position)

    def add_cash(
        self,
        cash: ImportedCash,
    ) -> None:
        """
        Adds an imported cash balance.
        """
        self.cash.append(cash)

    def __str__(self) -> str:
        """
        Returns a concise description of the imported account.
        """
        return (
            f"{self.account_name} "
            f"({self.number_of_positions} positions, "
            f"{self.number_of_cash_balances} cash balances)"
        )