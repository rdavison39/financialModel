"""
Service for retrieving historical portfolio values and benchmark performance.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.portfolio_snapshot import PortfolioSnapshot


@dataclass(frozen=True)
class PortfolioHistoryPoint:
    """A portfolio value at a particular valuation date."""

    snapshot_date: date
    total_value: Decimal


@dataclass(frozen=True)
class BenchmarkHistoryPoint:
    """A benchmark closing value at a particular date."""

    snapshot_date: date
    value: Decimal


class PortfolioHistoryService:
    """Retrieve historical portfolio and benchmark values."""

    BENCHMARKS: dict[str, str] = {
        "S&P 500": "^GSPC",
        "TSX Composite": "^GSPTSE",
    }

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
        """Return portfolio snapshots between two dates."""
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

    def get_aggregated_history(
        self,
        start_date: date,
        end_date: date,
        account_ids: list[int],
    ) -> list[PortfolioHistoryPoint]:
        """
        Return historical values aggregated across selected accounts.

        The graph is built from individual account snapshots rather than the
        persisted consolidated snapshot. This keeps graph account selection
        independent from the Portfolio Include setting.

        For each valuation date, the latest known snapshot on or before that
        date is used for each selected account.
        """
        if start_date > end_date or not account_ids:
            return []

        unique_account_ids = list(dict.fromkeys(account_ids))

        snapshots = list(
            self.session.scalars(
                select(PortfolioSnapshot)
                .where(
                    PortfolioSnapshot.account_id.in_(unique_account_ids),
                    PortfolioSnapshot.snapshot_date <= end_date,
                )
                .order_by(
                    PortfolioSnapshot.account_id,
                    PortfolioSnapshot.snapshot_date,
                )
            ).all()
        )

        snapshots_by_account: dict[int, list[PortfolioSnapshot]] = {
            account_id: [] for account_id in unique_account_ids
        }

        for snapshot in snapshots:
            if snapshot.account_id is not None:
                snapshots_by_account[snapshot.account_id].append(snapshot)

        valuation_dates = sorted(
            {
                snapshot.snapshot_date
                for snapshot in snapshots
                if start_date <= snapshot.snapshot_date <= end_date
            }
        )

        if not valuation_dates:
            return []

        result: list[PortfolioHistoryPoint] = []

        for valuation_date in valuation_dates:
            total = Decimal("0")
            have_value = False

            for account_id in unique_account_ids:
                account_snapshots = snapshots_by_account.get(account_id, [])
                if not account_snapshots:
                    continue

                snapshot_dates = [
                    snapshot.snapshot_date
                    for snapshot in account_snapshots
                ]
                position = bisect_right(
                    snapshot_dates,
                    valuation_date,
                ) - 1

                if position < 0:
                    continue

                total += Decimal(
                    str(account_snapshots[position].total_value)
                )
                have_value = True

            if have_value:
                result.append(
                    PortfolioHistoryPoint(
                        snapshot_date=valuation_date,
                        total_value=total,
                    )
                )

        return result

    def get_benchmark_history(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[BenchmarkHistoryPoint]:
        """
        Return daily benchmark closes from Yahoo Finance.

        The returned values are only used for percentage comparison, so the
        benchmark's quoted currency does not need to be converted to CAD.
        """
        if not symbol.strip() or start_date > end_date:
            return []

        try:
            import yfinance as yf
        except ImportError as exc:
            raise RuntimeError(
                "Benchmark comparison requires the yfinance package."
            ) from exc

        ticker = yf.Ticker(symbol.strip())

        # Yahoo's end date is exclusive, so include one day after the requested
        # end date.  auto_adjust=False keeps the downloaded Close column
        # explicit and predictable.
        history = ticker.history(
            start=start_date.isoformat(),
            end=(end_date + timedelta(days=1)).isoformat(),
            interval="1d",
            auto_adjust=False,
        )

        if history is None or history.empty:
            return []

        result: list[BenchmarkHistoryPoint] = []

        for index, row in history.iterrows():
            close = row.get("Close")
            if close is None:
                continue

            try:
                value = Decimal(str(close))
            except Exception:
                continue

            if value <= 0:
                continue

            timestamp = index
            if hasattr(timestamp, "date"):
                point_date = timestamp.date()
            else:
                point_date = date.fromisoformat(str(timestamp)[:10])

            if start_date <= point_date <= end_date:
                result.append(
                    BenchmarkHistoryPoint(
                        snapshot_date=point_date,
                        value=value,
                    )
                )

        return result
