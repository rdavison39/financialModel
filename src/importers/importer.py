"""
importer.py

Defines the abstract base class for all brokerage importers.

An Importer reads brokerage export files and converts them into DTOs.

Importers do not access the database.

Importers do not contain business logic.

Importers simply convert brokerage exports into a standardized set of
DTOs that can be processed by the ImportService.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from src.dto.imported_account import ImportedAccount
from src.dto.imported_position import ImportedPosition


class Importer(ABC):
    """
    Abstract base class for brokerage importers.
    """

    @abstractmethod
    def read_accounts(
        self,
    ) -> list[ImportedAccount]:
        """
        Read all accounts from the brokerage export.

        Returns:
            List of ImportedAccount DTOs.
        """

        raise NotImplementedError

    @abstractmethod
    def read_positions(
        self,
    ) -> list[ImportedPosition]:
        """
        Read all investment positions from the brokerage export.

        Returns:
            List of ImportedPosition DTOs.
        """

        raise NotImplementedError