"""
Service for comparing portfolio positions and values between two dates.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.company import Company
from src.models.holding_snapshot import HoldingSnapshot
from src.models.import_record import ImportRecord
from src.models.portfolio_snapshot import PortfolioSnapshot


@dataclass
class PositionComparison:
    """Comparison of one security between two dates."""

    symbol: str
    company_name: str
    first_quantity: Decimal
    second_quantity: Decimal
    quantity_difference: Decimal


@dataclass
class PortfolioComparison:
    """Complete portfolio comparison between two dates."""

    first_value: Decimal | None
    second_value: Decimal | None
    value_difference: Decimal | None
    positions: list[PositionComparison]


class PortfolioComparisonService:
    """Compares portfolio positions and values between two dates."""

    def __init__(self, session: Session) -> None:
        """Initialize the comparison service."""
        self.session = session

    def compare(
        self,
        first_date: date,
        second_date: date,
        account_id: int | None = None,
    ) -> PortfolioComparison:
        """
        Compare portfolio values and positions between two dates.

        The latest portfolio valuation on or before each requested date
        is used for portfolio values.

        The latest imported account snapshot on or before each requested
        date is used for position quantities.

        An account_id of None means the consolidated portfolio.
        """

        first_value = self._get_portfolio_value(
            first_date,
            account_id,
        )

        second_value = self._get_portfolio_value(
            second_date,
            account_id,
        )

        value_difference: Decimal | None = None

        if first_value is not None and second_value is not None:
            value_difference = second_value - first_value

        positions = self.compare_positions(
            first_date=first_date,
            second_date=second_date,
            account_id=account_id,
        )

        return PortfolioComparison(
            first_value=first_value,
            second_value=second_value,
            value_difference=value_difference,
            positions=positions,
        )

    def compare_positions(
        self,
        first_date: date,
        second_date: date,
        account_id: int | None = None,
    ) -> list[PositionComparison]:
        """
        Compare portfolio positions between two dates.

        An account_id of None means all accounts combined.

        For an individual account, the latest complete imported
        snapshot on or before each requested date is used.
        """

        if account_id is None:
            return self._compare_consolidated(
                first_date,
                second_date,
            )

        first_snapshot = self._get_snapshot_date(
            account_id,
            first_date,
        )

        second_snapshot = self._get_snapshot_date(
            account_id,
            second_date,
        )

        first_positions = self._get_positions(
            account_id,
            first_snapshot,
        )

        second_positions = self._get_positions(
            account_id,
            second_snapshot,
        )

        return self._build_comparison(
            first_positions,
            second_positions,
        )

    def _get_portfolio_value(
        self,
        requested_date: date,
        account_id: int | None,
    ) -> Decimal | None:
        """
        Return the latest portfolio valuation on or before a date.
        """

        snapshot = self.session.scalar(
            select(PortfolioSnapshot)
            .where(
                PortfolioSnapshot.account_id == account_id,
                PortfolioSnapshot.snapshot_date <= requested_date,
            )
            .order_by(
                PortfolioSnapshot.snapshot_date.desc()
            )
            .limit(1)
        )

        if snapshot is None:
            return None

        return snapshot.total_value

    def _get_snapshot_date(
        self,
        account_id: int,
        requested_date: date,
    ) -> datetime | None:
        """
        Return the latest imported snapshot on the requested date
        or any earlier date.
        """

        end_of_requested_date = datetime.combine(
            requested_date + timedelta(days=1),
            time.min,
        )

        snapshot = self.session.scalar(
            select(ImportRecord)
            .where(
                ImportRecord.account_id == account_id,
                ImportRecord.snapshot_date < end_of_requested_date,
            )
            .order_by(
                ImportRecord.snapshot_date.desc()
            )
            .limit(1)
        )

        if snapshot is None:
            return None

        return snapshot.snapshot_date

    def _get_positions(
        self,
        account_id: int,
        snapshot_date: datetime | None,
    ) -> dict[str, tuple[str, Decimal]]:
        """Return positions for an account snapshot."""

        if snapshot_date is None:
            return {}

        rows = self.session.execute(
            select(
                Company.symbol,
                Company.name,
                HoldingSnapshot.quantity,
            )
            .join(
                HoldingSnapshot,
                HoldingSnapshot.company_id == Company.id,
            )
            .where(
                HoldingSnapshot.account_id == account_id,
                HoldingSnapshot.snapshot_date == snapshot_date,
            )
        ).all()

        return {
            symbol: (company_name, quantity)
            for symbol, company_name, quantity in rows
        }

    def _compare_consolidated(
        self,
        first_date: date,
        second_date: date,
    ) -> list[PositionComparison]:
        """Compare positions across all accounts."""

        account_ids = self._get_account_ids()

        first_positions: dict[str, tuple[str, Decimal]] = {}
        second_positions: dict[str, tuple[str, Decimal]] = {}

        for account_id in account_ids:
            first_account_positions = self._get_positions(
                account_id,
                self._get_snapshot_date(
                    account_id,
                    first_date,
                ),
            )

            second_account_positions = self._get_positions(
                account_id,
                self._get_snapshot_date(
                    account_id,
                    second_date,
                ),
            )

            self._add_positions(
                first_positions,
                first_account_positions,
            )

            self._add_positions(
                second_positions,
                second_account_positions,
            )

        return self._build_comparison(
            first_positions,
            second_positions,
        )

    def _get_account_ids(self) -> list[int]:
        """Return all account IDs."""

        from src.models.account import Account

        return list(
            self.session.scalars(
                select(Account.id).order_by(Account.id)
            ).all()
        )

    def _add_positions(
        self,
        target: dict[str, tuple[str, Decimal]],
        source: dict[str, tuple[str, Decimal]],
    ) -> None:
        """Add positions from one account into a consolidated total."""

        for symbol, (company_name, quantity) in source.items():
            if symbol in target:
                existing_name, existing_quantity = target[symbol]

                target[symbol] = (
                    existing_name,
                    existing_quantity + quantity,
                )
            else:
                target[symbol] = (
                    company_name,
                    quantity,
                )

    def _build_comparison(
        self,
        first_positions: dict[str, tuple[str, Decimal]],
        second_positions: dict[str, tuple[str, Decimal]],
    ) -> list[PositionComparison]:
        """Build position comparisons from two position sets."""

        symbols = sorted(
            set(first_positions) | set(second_positions)
        )

        comparisons: list[PositionComparison] = []

        for symbol in symbols:
            first_name, first_quantity = first_positions.get(
                symbol,
                ("", Decimal("0")),
            )

            second_name, second_quantity = second_positions.get(
                symbol,
                (first_name, Decimal("0")),
            )

            company_name = second_name or first_name

            comparisons.append(
                PositionComparison(
                    symbol=symbol,
                    company_name=company_name,
                    first_quantity=first_quantity,
                    second_quantity=second_quantity,
                    quantity_difference=(
                        second_quantity - first_quantity
                    ),
                )
            )

        return comparisons