"""
import_service.py

Implements the ImportService.

The ImportService bridges the importer layer and the persistence layer.
It accepts imported DTO objects, validates them, persists them using
repositories, and returns an ImportResult summarizing the operation.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from src.dto.imported_account import ImportedAccount
from src.services.import_result import ImportResult


class ImportService:
    """
    Imports brokerage data into the database.
    """

    def __init__(self, session: Session) -> None:
        """
        Initializes the service.

        Args:
            session:
                SQLAlchemy session.
        """
        self._session = session

    def import_data(
        self,
        accounts: list[ImportedAccount],
        source_file: Path,
    ) -> ImportResult:
        """
        Imports one brokerage export.

        Args:
            accounts:
                Imported brokerage accounts.

            source_file:
                Workbook that produced the DTOs.

        Returns:
            ImportResult summarizing the import.
        """
        result = ImportResult()

        try:
            self._validate(accounts)

            import_record = self._create_import(
                source_file=source_file,
                account_count=len(accounts),
            )

            result.import_id = import_record.id

            for account in accounts:
                self._process_account(
                    account=account,
                    import_record=import_record,
                    result=result,
                )

            self._session.commit()

            result.mark_success()

        except Exception:
            self._session.rollback()
            raise

        return result

    def _validate(
        self,
        accounts: list[ImportedAccount],
    ) -> None:
        """
        Validates imported DTOs.

        Validation implementation will be added later.
        """
        return

    def _create_import(
        self,
        source_file: Path,
        account_count: int,
    ):
        """
        Creates an Import record.

        Implementation added later.
        """
        raise NotImplementedError

    def _process_account(
        self,
        account: ImportedAccount,
        import_record,
        result: ImportResult,
    ) -> None:
        """
        Processes one brokerage account.
        """
        raise NotImplementedError

    def _find_or_create_brokerage(
        self,
        name: str,
    ):
        """
        Finds or creates a Brokerage.
        """
        raise NotImplementedError

    def _find_or_create_account(
        self,
        account: ImportedAccount,
        brokerage,
    ):
        """
        Finds or creates an Account.
        """
        raise NotImplementedError

    def _find_or_create_company(
        self,
        ticker: str,
        description: str,
    ):
        """
        Finds or creates a Company.
        """
        raise NotImplementedError

    def _create_holding_snapshot(
        self,
        position,
        account,
        company,
        import_record,
    ) -> None:
        """
        Creates one HoldingSnapshot.
        """
        raise NotImplementedError

    def _create_cash_snapshot(
        self,
        cash,
        account,
        import_record,
    ) -> None:
        """
        Creates one CashBalanceSnapshot.
        """
        raise NotImplementedError