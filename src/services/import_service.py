"""
Service for importing brokerage portfolio snapshots.

Historical portfolio data is maintained at one snapshot per account per
calendar day.  A newer brokerage report for the same day replaces the
existing daily snapshot.  An identical or older report is skipped.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.models.account import Account
from src.models.brokerage import Brokerage
from src.models.cash_snapshot import CashSnapshot
from src.models.company import Company
from src.models.holding_snapshot import HoldingSnapshot
from src.models.import_record import ImportRecord


@dataclass
class ImportResult:
    """Result of importing one brokerage snapshot."""

    account_number: str
    snapshot_date: datetime
    holdings_imported: int
    cash_imported: int
    duplicate: bool


class ImportService:
    """Stores imported brokerage snapshots in the database."""

    def __init__(self, session: Session) -> None:
        """Initialize the import service."""
        self.session = session

    def import_snapshot(
        self,
        brokerage_name: str,
        imported_account,
        file_name: str,
    ) -> ImportResult:
        """
        Import one complete brokerage account snapshot.

        There is one financial snapshot per account per calendar day.

        - No existing snapshot for the day: create it.
        - Same source timestamp: skip it.
        - Older source timestamp: skip it.
        - Newer source timestamp: replace the existing daily snapshot.
        """

        brokerage = self._get_or_create_brokerage(brokerage_name)

        account = self._get_or_create_account(
            brokerage=brokerage,
            account_number=imported_account.account_number,
        )

        incoming_timestamp = imported_account.snapshot_date
        incoming_day = incoming_timestamp.date()

        existing_imports = list(
            self.session.scalars(
                select(ImportRecord)
                .where(
                    ImportRecord.brokerage_id == brokerage.id,
                    ImportRecord.account_id == account.id,
                )
                .order_by(
                    ImportRecord.snapshot_date.desc()
                )
            ).all()
        )

        same_day_imports = [
            item
            for item in existing_imports
            if item.snapshot_date.date() == incoming_day
        ]

        # An identical timestamp is the same source snapshot.  Do not
        # create duplicate data.
        if any(
            item.snapshot_date == incoming_timestamp
            for item in same_day_imports
        ):
            return self._skipped_result(imported_account)

        # If a newer snapshot for this day already exists, the incoming
        # file must not overwrite the current daily source of truth.
        if any(
            item.snapshot_date > incoming_timestamp
            for item in same_day_imports
        ):
            return self._skipped_result(imported_account)

        # A newer snapshot for the same day replaces every existing
        # snapshot for that day.  This also cleans up any legacy duplicate
        # ImportRecord rows that may have been created before the daily
        # upsert rule was introduced.
        for existing_import in same_day_imports:
            self._delete_snapshot(
                account_id=account.id,
                snapshot_date=existing_import.snapshot_date,
            )

            self.session.delete(existing_import)

        import_record = ImportRecord(
            brokerage_id=brokerage.id,
            account_id=account.id,
            snapshot_date=incoming_timestamp,
            file_name=file_name,
        )

        self.session.add(import_record)

        holdings_imported = 0

        for imported_holding in imported_account.holdings:
            company = self._get_or_create_company(
                symbol=imported_holding.symbol,
                company_name=imported_holding.company_name,
            )

            holding = HoldingSnapshot(
                account_id=account.id,
                company_id=company.id,
                snapshot_date=incoming_timestamp,
                quantity=imported_holding.quantity,
                average_cost=imported_holding.average_cost,
                price=imported_holding.price,
                market_value=imported_holding.market_value,
                unrealized_gain=imported_holding.unrealized_gain,
                unrealized_gain_percent=(
                    imported_holding.unrealized_gain_percent
                ),
                daily_change=imported_holding.daily_change,
                daily_change_percent=(
                    imported_holding.daily_change_percent
                ),
                previous_close=imported_holding.previous_close,
                currency=imported_holding.currency,
            )

            self.session.add(holding)
            holdings_imported += 1

        cash_imported = 0

        for imported_cash in imported_account.cash:
            cash = CashSnapshot(
                account_id=account.id,
                snapshot_date=incoming_timestamp,
                currency=imported_cash.currency,
                amount=imported_cash.amount,
            )

            self.session.add(cash)
            cash_imported += 1

        self.session.commit()

        return ImportResult(
            account_number=imported_account.account_number,
            snapshot_date=incoming_timestamp,
            holdings_imported=holdings_imported,
            cash_imported=cash_imported,
            duplicate=False,
        )

    @staticmethod
    def _skipped_result(imported_account) -> ImportResult:
        """Return the standard result for an ignored source snapshot."""
        return ImportResult(
            account_number=imported_account.account_number,
            snapshot_date=imported_account.snapshot_date,
            holdings_imported=0,
            cash_imported=0,
            duplicate=True,
        )

    def _delete_snapshot(
        self,
        account_id: int,
        snapshot_date: datetime,
    ) -> None:
        """Delete imported holdings and cash for one source timestamp."""

        self.session.execute(
            delete(HoldingSnapshot).where(
                HoldingSnapshot.account_id == account_id,
                HoldingSnapshot.snapshot_date == snapshot_date,
            )
        )

        self.session.execute(
            delete(CashSnapshot).where(
                CashSnapshot.account_id == account_id,
                CashSnapshot.snapshot_date == snapshot_date,
            )
        )

    def _get_or_create_brokerage(
        self,
        brokerage_name: str,
    ) -> Brokerage:
        """Find a brokerage or create it."""
        brokerage = self.session.scalar(
            select(Brokerage).where(
                Brokerage.name == brokerage_name
            )
        )

        if brokerage is None:
            brokerage = Brokerage(name=brokerage_name)
            self.session.add(brokerage)
            self.session.flush()

        return brokerage

    def _get_or_create_account(
        self,
        brokerage: Brokerage,
        account_number: str,
    ) -> Account:
        """Find an account or create it."""
        account = self.session.scalar(
            select(Account).where(
                Account.brokerage_id == brokerage.id,
                Account.account_number == account_number,
            )
        )

        if account is None:
            account = Account(
                brokerage_id=brokerage.id,
                account_number=account_number,
                name=account_number,
            )
            self.session.add(account)
            self.session.flush()

        return account

    def _get_or_create_company(
        self,
        symbol: str,
        company_name: str,
    ) -> Company:
        """Find a company or create it."""
        company = self.session.scalar(
            select(Company).where(
                Company.symbol == symbol
            )
        )

        if company is None:
            company = Company(
                symbol=symbol,
                name=company_name,
            )
            self.session.add(company)
            self.session.flush()

        elif company.name != company_name and company_name:
            company.name = company_name

        return company
