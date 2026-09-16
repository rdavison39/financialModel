"""
Service for retrieving historical portfolio values.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.portfolio_snapshot import PortfolioSnapshot


class PortfolioHistoryService:
    """Retrieves historical account and consolidated portfolio values."""

    def __init__(self, session: Session) -> None:
        """Initialize the history service."""
        self.session = session

    def get_value_on_or_before(
        self,
        snapshot_date: date,
        account_id: int | None = None,
    ) -> Decimal | None:
        """
        Return the latest value on or before the requested date.

        An account_id of None means the consolidated portfolio.
        """

        snapshot = self.session.scalar(
            select(PortfolioSnapshot)
            .where(
                PortfolioSnapshot.account_id == account_id,
                PortfolioSnapshot.snapshot_date <= snapshot_date,
            )
            .order_by(PortfolioSnapshot.snapshot_date.desc())
            .limit(1)
        )

        if snapshot is None:
            return None

        return snapshot.total_value

    def get_history(
        self,
        start_date: date,
        end_date: date,
        account_id: int | None = None,
    ) -> list[PortfolioSnapshot]:
        """
        Return portfolio snapshots between two dates.

        An account_id of None means the consolidated portfolio.
        """

        return list(
            self.session.scalars(
                select(PortfolioSnapshot)
                .where(
                    PortfolioSnapshot.account_id == account_id,
                    PortfolioSnapshot.snapshot_date >= start_date,
                    PortfolioSnapshot.snapshot_date <= end_date,
                )
                .order_by(PortfolioSnapshot.snapshot_date)
            ).all()
        )