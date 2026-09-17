"""
Service for importing brokerage portfolio snapshots.

Import rules:
    - One authoritative brokerage snapshot per account per calendar day.
    - A same-day import with an older source timestamp is skipped.
    - A same-day import with the exact same source timestamp is skipped.
    - A same-day import with a newer source timestamp replaces the
      existing snapshot and all of its holding/cash rows.
    - A different calendar day creates a new historical snapshot.
    - A forced re-import replaces an existing snapshot even when its
      source timestamp is identical.
"""

from dataclasses import dataclass
from datetime import date, datetime
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
    replaced: bool = False


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
        force_reimport: bool = False,
    ) -> ImportResult:
        """
        Import one complete brokerage account snapshot.

        The imported account's snapshot_date is the source timestamp from
        the brokerage report. The calendar portion of that timestamp is the
        daily snapshot key.
        """
        snapshot_timestamp = imported_account.snapshot_date

        if not isinstance(snapshot_timestamp, datetime):
            raise TypeError(
                "imported_account.snapshot_date must be a datetime."
            )

        snapshot_day = snapshot_timestamp.date()

        brokerage = self._get_or_create_brokerage(brokerage_name)

        account = self._get_or_create_account(
            brokerage=brokerage,
            account_number=imported_account.account_number,
        )

        existing_import = self.session.scalar(
            select(ImportRecord).where(
                ImportRecord.brokerage_id == brokerage.id,
                ImportRecord.account_id == account.id,
                ImportRecord.snapshot_day == snapshot_day,
            )
        )

        if existing_import is not None:
            # Same or older source report: the existing snapshot remains
            # authoritative unless an explicit force re-import was requested.
            # A force re-import is intended for correcting a previously
            # imported snapshot after fixing the importer or source data.
            if (
                not force_reimport
                and snapshot_timestamp <= existing_import.snapshot_date
            ):
                return ImportResult(
                    account_number=imported_account.account_number,
                    snapshot_date=snapshot_timestamp,
                    holdings_imported=0,
                    cash_imported=0,
                    duplicate=True,
                    replaced=False,
                )

            # Newer report for the same calendar day, or an explicit force
            # re-import: remove the old snapshot completely before storing
            # the new source of truth.
            self._delete_snapshot_rows(
                account_id=account.id,
                snapshot_timestamp=existing_import.snapshot_date,
            )

            self.session.delete(existing_import)
            self.session.flush()

            replaced = True
        else:
            replaced = False

        import_record = ImportRecord(
            brokerage_id=brokerage.id,
            account_id=account.id,
            snapshot_date=snapshot_timestamp,
            snapshot_day=snapshot_day,
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
                snapshot_date=snapshot_timestamp,
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
                snapshot_date=snapshot_timestamp,
                currency=imported_cash.currency,
                amount=imported_cash.amount,
            )

            self.session.add(cash)
            cash_imported += 1

        self.session.commit()

        return ImportResult(
            account_number=imported_account.account_number,
            snapshot_date=snapshot_timestamp,
            holdings_imported=holdings_imported,
            cash_imported=cash_imported,
            duplicate=False,
            replaced=replaced,
        )

    def _delete_snapshot_rows(
        self,
        account_id: int,
        snapshot_timestamp: datetime,
    ) -> None:
        """Delete all holding and cash rows belonging to one import."""
        self.session.execute(
            delete(HoldingSnapshot).where(
                HoldingSnapshot.account_id == account_id,
                HoldingSnapshot.snapshot_date == snapshot_timestamp,
            )
        )

        self.session.execute(
            delete(CashSnapshot).where(
                CashSnapshot.account_id == account_id,
                CashSnapshot.snapshot_date == snapshot_timestamp,
            )
        )

        self.session.flush()

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
