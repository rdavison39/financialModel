"""Shared management of brokerage import snapshots and external cash flows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.account import Account
from src.models.brokerage import Brokerage
from src.models.import_record import ImportRecord
from src.models.portfolio_snapshot import PortfolioSnapshot


@dataclass(frozen=True)
class SnapshotAccount:
    """Account choice for snapshot management."""

    account_id: int
    brokerage_name: str
    account_number: str
    account_name: str

    @property
    def key(self) -> str:
        return f"{self.brokerage_name}|{self.account_number}|{self.account_name}"

    @property
    def label(self) -> str:
        return f"{self.brokerage_name} — {self.account_name} ({self.account_number})"


@dataclass(frozen=True)
class ManagedSnapshot:
    """One authoritative imported brokerage snapshot."""

    id: int
    account_id: int
    account_label: str
    snapshot_date: datetime | date
    total_value: Decimal | None
    external_added: Decimal
    external_withdrawn: Decimal


class SnapshotManagementService:
    """Shared business logic used by the desktop and web snapshot screens."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_accounts(self) -> list[SnapshotAccount]:
        rows = self.session.execute(
            select(Account, Brokerage)
            .join(Brokerage, Brokerage.id == Account.brokerage_id)
            .order_by(Brokerage.name, Account.account_number)
        ).all()
        return [
            SnapshotAccount(
                account_id=account.id,
                brokerage_name=brokerage.name,
                account_number=str(account.account_number),
                account_name=str(account.name or ""),
            )
            for account, brokerage in rows
        ]

    def get_snapshots(self, account_id: int | None = None) -> list[ManagedSnapshot]:
        """Return imported snapshots, one authoritative row per calendar day.

        Imported brokerage records are the source of truth for this screen.
        A PortfolioSnapshot fallback is retained for compatibility with older
        databases/tests that predate ImportRecord-based snapshot management.
        """
        statement = (
            select(ImportRecord, Account, Brokerage)
            .join(Account, Account.id == ImportRecord.account_id)
            .join(Brokerage, Brokerage.id == Account.brokerage_id)
            .order_by(ImportRecord.snapshot_day.desc(), ImportRecord.snapshot_date.desc())
        )
        if account_id is not None:
            statement = statement.where(ImportRecord.account_id == account_id)

        rows = self.session.execute(statement).all()
        if rows:
            result: list[ManagedSnapshot] = []
            for record, account, brokerage in rows:
                valuation = self.session.scalar(
                    select(PortfolioSnapshot)
                    .where(
                        PortfolioSnapshot.account_id == account.id,
                        PortfolioSnapshot.snapshot_date == record.snapshot_day,
                    )
                    .order_by(PortfolioSnapshot.id.desc())
                    .limit(1)
                )
                result.append(
                    ManagedSnapshot(
                        id=record.id,
                        account_id=account.id,
                        account_label=(
                            f"{brokerage.name} — "
                            f"{account.name or account.account_number}"
                        ),
                        snapshot_date=record.snapshot_date,
                        total_value=(
                            Decimal(str(valuation.total_value))
                            if valuation is not None
                            else None
                        ),
                        external_added=Decimal(str(record.external_added or 0)),
                        external_withdrawn=Decimal(str(record.external_withdrawn or 0)),
                    )
                )
            return result

        # Backward-compatible fallback for databases/tests that only have
        # PortfolioSnapshot rows. Keep the newest row for each date.
        valuation_statement = select(PortfolioSnapshot).order_by(
            PortfolioSnapshot.snapshot_date.desc(),
            PortfolioSnapshot.id.desc(),
        )
        if account_id is not None:
            valuation_statement = valuation_statement.where(
                PortfolioSnapshot.account_id == account_id
            )

        valuations = list(self.session.scalars(valuation_statement).all())
        seen_dates: set[date] = set()
        result = []
        for snapshot in valuations:
            if snapshot.snapshot_date in seen_dates:
                continue
            seen_dates.add(snapshot.snapshot_date)
            account = self.session.get(Account, snapshot.account_id) if snapshot.account_id else None
            brokerage = (
                self.session.get(Brokerage, account.brokerage_id)
                if account is not None
                else None
            )
            result.append(
                ManagedSnapshot(
                    id=snapshot.id,
                    account_id=snapshot.account_id or 0,
                    account_label=(
                        f"{brokerage.name} — {account.name or account.account_number}"
                        if account is not None and brokerage is not None
                        else "Portfolio"
                    ),
                    snapshot_date=snapshot.snapshot_date,
                    total_value=Decimal(str(snapshot.total_value)),
                    external_added=Decimal(str(snapshot.external_added or 0)),
                    external_withdrawn=Decimal(str(snapshot.external_withdrawn or 0)),
                )
            )
        return result

    def update_cash_flow(
        self,
        snapshot_id: int,
        external_added: Decimal | str | int | float,
        external_withdrawn: Decimal | str | int | float,
    ) -> ManagedSnapshot:
        """Update external cash-flow amounts for an imported snapshot."""
        added = self._amount(external_added, "$ Added")
        withdrawn = self._amount(external_withdrawn, "$ Withdrawn")

        record = self.session.get(ImportRecord, snapshot_id)
        if record is not None:
            record.external_added = added
            record.external_withdrawn = withdrawn
            account_id = record.account_id
        else:
            # Compatibility with legacy PortfolioSnapshot identifiers.
            snapshot = self.session.get(PortfolioSnapshot, snapshot_id)
            if snapshot is None:
                raise ValueError("Snapshot not found.")
            snapshot.external_added = added
            snapshot.external_withdrawn = withdrawn
            account_id = snapshot.account_id

        self.session.commit()
        for managed in self.get_snapshots(account_id):
            if managed.id == snapshot_id:
                return managed
        raise ValueError("Snapshot not found.")

    @staticmethod
    def _amount(value, field_name: str) -> Decimal:
        try:
            amount = Decimal(str(value).strip() or "0")
        except (InvalidOperation, ValueError, AttributeError) as exc:
            raise ValueError(f"{field_name} must be a valid dollar amount.") from exc
        if amount < 0:
            raise ValueError(f"{field_name} cannot be negative.")
        return amount.quantize(Decimal("0.01"))
