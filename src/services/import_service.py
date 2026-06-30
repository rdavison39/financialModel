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

from decimal import Decimal
from pathlib import Path

from src.database.unit_of_work import UnitOfWork
from src.dto.imported_account import ImportedAccount
from src.dto.imported_cash import ImportedCash
from src.dto.imported_position import ImportedPosition
from src.models.account import Account
from src.models.brokerage import Brokerage
from src.models.cash_balance_snapshot import CashBalanceSnapshot
from src.models.company import Company
from src.models.holding_snapshot import HoldingSnapshot
from src.models.import_record import Import
from src.services.import_result import ImportResult
from src.services.service_base import ServiceBase


class ImportService(ServiceBase):
    """
    Imports brokerage DTO data into the database.
    """

    BROKERAGE_NAME = "BMO InvestorLine"
    BROKERAGE_IMPORTER = "BMOInvestorLineImporter"
    BROKERAGE_WEBSITE = "https://www.bmo.com/investorline"

    DEFAULT_OWNER = "Unknown"
    DEFAULT_ACCOUNT_CURRENCY = "CAD"
    DEFAULT_EXCHANGE = "Unknown"
    DEFAULT_SECTOR = "Unknown"
    DEFAULT_INDUSTRY = "Unknown"
    DEFAULT_COUNTRY = "Unknown"

    ZERO = Decimal("0")

    def __init__(
        self,
        uow: UnitOfWork,
    ) -> None:
        """
        Initialize the service.

        Args:
            uow:
                UnitOfWork used for repository access and transactions.
        """

        super().__init__(uow)

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

            brokerage, brokerage_created = (
                self._find_or_create_brokerage()
            )
            self.flush()

            if brokerage_created:
                result.brokerages_created += 1

            import_record = self._create_import(
                brokerage=brokerage,
                source_file=source_file,
                account_count=len(accounts),
                holding_count=self._count_positions(accounts),
            )
            self.flush()

            result.import_id = import_record.id

            for account in accounts:
                self._process_account(
                    account=account,
                    brokerage=brokerage,
                    import_record=import_record,
                    result=result,
                )

            self.commit()
            result.mark_success()

        except Exception:
            self.rollback()
            raise

        return result

    def _validate(
        self,
        accounts: list[ImportedAccount],
    ) -> None:
        """
        Validate imported DTOs before any database changes.
        """

        if not accounts:
            raise ValueError("At least one imported account is required.")

        for account in accounts:
            self._validate_account(account)

    def _validate_account(
        self,
        account: ImportedAccount,
    ) -> None:
        """
        Validate one imported account.
        """

        if not account.account_number:
            raise ValueError("Imported account is missing account number.")

        if not account.account_name:
            raise ValueError("Imported account is missing account name.")

        if not account.account_type:
            raise ValueError("Imported account is missing account type.")

        if account.number_of_positions == 0:
            raise ValueError(
                f"Account {account.account_number} has no positions."
            )

        currencies: set[str] = set()

        for cash in account.cash:
            self._validate_cash(cash)

            if cash.currency in currencies:
                raise ValueError(
                    "Duplicate cash balance currency "
                    f"{cash.currency} for account "
                    f"{account.account_number}."
                )

            currencies.add(cash.currency)

        for position in account.positions:
            self._validate_position(position)

    def _validate_cash(
        self,
        cash: ImportedCash,
    ) -> None:
        """
        Validate one imported cash balance.
        """

        if not cash.currency:
            raise ValueError("Imported cash balance is missing currency.")

        if cash.amount is None:
            raise ValueError("Imported cash balance is missing amount.")

    def _validate_position(
        self,
        position: ImportedPosition,
    ) -> None:
        """
        Validate one imported holding.
        """

        if not position.symbol:
            raise ValueError("Imported position is missing symbol.")

        if not position.description:
            raise ValueError(
                f"Imported position {position.symbol} "
                "is missing description."
            )

        if not position.currency:
            raise ValueError(
                f"Imported position {position.symbol} "
                "is missing currency."
            )

        if position.quantity < self.ZERO:
            raise ValueError(
                f"Imported position {position.symbol} "
                "has negative quantity."
            )

        if position.unit_price < self.ZERO:
            raise ValueError(
                f"Imported position {position.symbol} "
                "has negative unit price."
            )

        if position.market_value < self.ZERO:
            raise ValueError(
                f"Imported position {position.symbol} "
                "has negative market value."
            )

        if position.cost_basis < self.ZERO:
            raise ValueError(
                f"Imported position {position.symbol} "
                "has negative cost basis."
            )

    def _create_import(
        self,
        brokerage: Brokerage,
        source_file: Path,
        account_count: int,
        holding_count: int,
    ) -> Import:
        """
        Create an Import record.
        """

        import_record = Import(
            brokerage_id=brokerage.id,
            source_folder=str(source_file.parent),
            file_count=1,
            account_count=account_count,
            holding_count=holding_count,
            validation_status="VALID",
            notes=f"Imported from {source_file.name}",
        )

        self.uow.imports.add(import_record)

        return import_record

    def _process_account(
        self,
        account: ImportedAccount,
        brokerage: Brokerage,
        import_record: Import,
        result: ImportResult,
    ) -> None:
        """
        Persist one imported brokerage account.
        """

        persisted_account, account_created = (
            self._find_or_create_account(
                account=account,
                brokerage=brokerage,
            )
        )
        self.flush()

        if account_created:
            result.accounts_created += 1

        result.accounts_imported += 1

        for cash in account.cash:
            self._create_cash_snapshot(
                cash=cash,
                account=persisted_account,
                import_record=import_record,
            )
            result.cash_balances_imported += 1

        for position in account.positions:
            company, company_created = (
                self._find_or_create_company(position)
            )
            self.flush()

            if company_created:
                result.companies_created += 1

            self._create_holding_snapshot(
                position=position,
                account=persisted_account,
                company=company,
                import_record=import_record,
            )
            result.positions_imported += 1

    def _find_or_create_brokerage(
        self,
    ) -> tuple[Brokerage, bool]:
        """
        Find or create the BMO InvestorLine brokerage.
        """

        brokerage = self.uow.brokerages.find_by_name(
            self.BROKERAGE_NAME
        )

        if brokerage is not None:
            return brokerage, False

        brokerage = self.uow.brokerages.create_if_missing(
            name=self.BROKERAGE_NAME,
            importer=self.BROKERAGE_IMPORTER,
            website=self.BROKERAGE_WEBSITE,
        )

        return brokerage, True

    def _find_or_create_account(
        self,
        account: ImportedAccount,
        brokerage: Brokerage,
    ) -> tuple[Account, bool]:
        """
        Find or create an Account.
        """

        persisted_account = (
            self.uow.accounts.find_by_account_number(
                brokerage.id,
                account.account_number,
            )
        )

        if persisted_account is not None:
            return persisted_account, False

        persisted_account = self.uow.accounts.create_if_missing(
            brokerage_id=brokerage.id,
            account_number=account.account_number,
            account_name=account.account_name,
            owner=self.DEFAULT_OWNER,
            account_type=account.account_type,
            currency=self._account_currency(account),
        )

        return persisted_account, True

    def _find_or_create_company(
        self,
        position: ImportedPosition,
    ) -> tuple[Company, bool]:
        """
        Find or create a Company.
        """

        company = self.uow.companies.find_by_ticker(
            position.symbol
        )

        if company is not None:
            return company, False

        company = self.uow.companies.create_if_missing(
            ticker=position.symbol,
            company_name=position.description,
            exchange=self.DEFAULT_EXCHANGE,
            currency=position.currency,
            asset_class=position.security_type or "Unknown",
            sector=self.DEFAULT_SECTOR,
            industry=self.DEFAULT_INDUSTRY,
            country=self.DEFAULT_COUNTRY,
        )

        return company, True

    def _create_holding_snapshot(
        self,
        position: ImportedPosition,
        account: Account,
        company: Company,
        import_record: Import,
    ) -> None:
        """
        Create one HoldingSnapshot.
        """

        holding = HoldingSnapshot(
            import_id=import_record.id,
            account_id=account.id,
            company_id=company.id,
            shares=position.quantity,
            average_cost=self._average_cost(position),
            total_cost=position.cost_basis,
            imported_price=position.unit_price,
            imported_market_value=position.market_value,
            imported_unrealized_gain=(
                position.market_value - position.cost_basis
            ),
            imported_dividend=self.ZERO,
            imported_yield=self.ZERO,
        )

        self.uow.holdings.add(holding)

    def _create_cash_snapshot(
        self,
        cash: ImportedCash,
        account: Account,
        import_record: Import,
    ) -> None:
        """
        Create one CashBalanceSnapshot.
        """

        snapshot = CashBalanceSnapshot(
            import_id=import_record.id,
            account_id=account.id,
            currency=cash.currency,
            cash_balance=cash.amount,
        )

        self.uow.cash_balances.add(snapshot)

    def _count_positions(
        self,
        accounts: list[ImportedAccount],
    ) -> int:
        """
        Count imported positions across all accounts.
        """

        return sum(
            account.number_of_positions
            for account in accounts
        )

    def _account_currency(
        self,
        account: ImportedAccount,
    ) -> str:
        """
        Determine the account currency from imported facts.
        """

        if account.cash:
            return account.cash[0].currency

        if account.positions:
            return account.positions[0].currency

        return self.DEFAULT_ACCOUNT_CURRENCY

    def _average_cost(
        self,
        position: ImportedPosition,
    ) -> Decimal:
        """
        Calculate average cost from imported total cost and quantity.
        """

        if position.quantity == self.ZERO:
            return self.ZERO

        return position.cost_basis / position.quantity
