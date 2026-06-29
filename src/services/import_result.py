"""
import_result.py

Defines the ImportResult data transfer object.

ImportResult summarizes the outcome of a brokerage import operation.
It provides callers with useful statistics without exposing SQLAlchemy
models or repository implementation details.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ImportResult:
    """
    Summarizes the outcome of an import operation.
    """

    #
    # Overall Status
    #

    success: bool = False

    #
    # Database
    #

    import_id: int | None = None

    #
    # Statistics
    #

    accounts_imported: int = 0
    positions_imported: int = 0
    cash_balances_imported: int = 0

    brokerages_created: int = 0
    accounts_created: int = 0
    companies_created: int = 0

    #
    # Diagnostics
    #

    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def has_warnings(self) -> bool:
        """
        Returns True if any warnings were generated.
        """
        return bool(self.warnings)

    @property
    def has_errors(self) -> bool:
        """
        Returns True if any errors were generated.
        """
        return bool(self.errors)

    def add_warning(self, message: str) -> None:
        """
        Adds a warning message.
        """
        self.warnings.append(message)

    def add_error(self, message: str) -> None:
        """
        Adds an error message.
        """
        self.errors.append(message)
        self.success = False

    def mark_success(self) -> None:
        """
        Marks the import as successful.
        """
        self.success = True

    def __str__(self) -> str:
        """
        Returns a concise summary of the import.
        """
        return (
            f"ImportResult("
            f"success={self.success}, "
            f"accounts={self.accounts_imported}, "
            f"positions={self.positions_imported}, "
            f"cash={self.cash_balances_imported}, "
            f"errors={len(self.errors)}, "
            f"warnings={len(self.warnings)})"
        )