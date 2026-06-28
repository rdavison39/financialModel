"""
import_service.py

Business service responsible for importing brokerage data into the
Davison Financial Model.

The ImportService coordinates the import process. It does not parse
brokerage files and it does not perform SQL queries directly.

Importers read files and produce DTOs.

Repositories persist entities.

The ImportService orchestrates the entire workflow.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from src.database.unit_of_work import UnitOfWork
from src.services.service_base import ServiceBase


class ImportService(ServiceBase):
    """
    Coordinates the import of brokerage data.

    Responsibilities
    ----------------
    * Validate imported DTOs.
    * Create Brokerage records when necessary.
    * Create Account records when necessary.
    * Create Company records when necessary.
    * Create an Import record.
    * Create HoldingSnapshot records.
    * Commit or roll back the transaction.
    """

    def __init__(
        self,
        uow: UnitOfWork,
    ) -> None:
        """
        Initialize the ImportService.
        """

        super().__init__(uow)

    def import_data(
        self,
    ) -> None:
        """
        Execute a brokerage import.

        This method will be implemented during the importer milestone.
        """

        raise NotImplementedError(
            "ImportService.import_data() has not yet been implemented."
        )

    #
    # Private Helper Methods
    #

    def _create_import_record(self) -> None:
        """
        Create the Import record.

        Implementation to follow.
        """

        raise NotImplementedError

    def _process_accounts(self) -> None:
        """
        Process imported accounts.

        Implementation to follow.
        """

        raise NotImplementedError

    def _process_companies(self) -> None:
        """
        Process imported companies.

        Implementation to follow.
        """

        raise NotImplementedError

    def _process_holdings(self) -> None:
        """
        Process imported holding snapshots.

        Implementation to follow.
        """

        raise NotImplementedError