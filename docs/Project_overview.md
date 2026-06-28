"""
imported_account.py

Defines the ImportedAccount data transfer object (DTO).

An ImportedAccount represents a single brokerage account read from
an export file. It contains the account information and every
ImportedPosition found in that account.

This object is independent of the database.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.dto.imported_position import ImportedPosition


@dataclass(slots=True)
class ImportedAccount:
    """
    Represents one imported brokerage account.
    """

    #
    # Account Information
    #

    account_number: str
    account_name: str
    owner: str
    brokerage: str
    account_type: str
    currency: str = "CAD"

    #
    # Positions
    #

    positions: list[ImportedPosition] = field(default_factory=list)

    @property
    def number_of_positions(self) -> int:
        """
        Returns the number of positions in the account.
        """
        return len(self.positions)

    def add_position(self, position: ImportedPosition) -> None:
        """
        Adds a position to the account.
        """
        self.positions.append(position)

    def __str__(self) -> str:
        return (
            f"{self.account_name} "
            f"({self.number_of_positions} positions)"
        )