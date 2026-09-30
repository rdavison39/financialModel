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
    """A portfolio valuation and its stored daily performance."""

    snapshot_date: date
    total_value: Decimal
    daily_change: Decimal | None = None
    daily_change_percent: Decimal | None = None


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
                daily_change: Decimal | None = Decimal("0")
                have_daily_change = True

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

                    account_change = getattr(
                        account_snapshots[position],
                        "daily_change",
                        None,
                    )
                    if account_change is None:
                        have_daily_change = False
                        break

                    daily_change += Decimal(str(account_change))

                if not have_daily_change:
                    daily_change = None

                daily_change_percent = None
                if daily_change is not None:
                    previous_value = total - daily_change
                    if previous_value != 0:
                        daily_change_percent = (
                            daily_change / previous_value * Decimal("100")
                        )
                    else:
                        daily_change_percent = Decimal("0")

                result.append(
                    PortfolioHistoryPoint(
                        snapshot_date=valuation_date,
                        total_value=total,
                        daily_change=daily_change,
                        daily_change_percent=daily_change_percent,
                    )
                )

        return result

    @staticmethod
    def calculate_growth_values(
        history: list[PortfolioHistoryPoint],
    ) -> list[Decimal]:
        """Calculate percentage growth from the first portfolio value."""
        if not history:
            return []

        first = Decimal(str(history[0].total_value))
        if first == 0:
            return [Decimal("0") for _ in history]

        return [
            (Decimal(str(point.total_value)) - first) / first * Decimal("100")
            for point in history
        ]

    @staticmethod
    def calculate_gain_loss_values(
        history: list[PortfolioHistoryPoint],
    ) -> list[Decimal]:
        """Calculate dollar gain/loss relative to the first portfolio value."""
        if not history:
            return []

        first = Decimal(str(history[0].total_value))
        return [
            Decimal(str(point.total_value)) - first
            for point in history
        ]

    @staticmethod
    def calculate_daily_change_values(
        history: list[PortfolioHistoryPoint],
    ) -> list[Decimal]:
        """Return stored daily dollar changes, with a value-change fallback."""
        if not history:
            return []

        result: list[Decimal] = []
        first = Decimal(str(history[0].total_value))

        for point in history:
            if point.daily_change is not None:
                change = Decimal(str(point.daily_change))
            else:
                # Compatibility fallback for history points that predate
                # stored daily-change fields.
                change = Decimal(str(point.total_value)) - first

            result.append(change)

        return result

    @staticmethod
    def calculate_daily_change_percent_values(
        history: list[PortfolioHistoryPoint],
    ) -> list[Decimal | None]:
        """Return stored daily percentages, with a value-change fallback."""
        if not history:
            return []

        result: list[Decimal | None] = []
        previous: Decimal | None = None

        for point in history:
            current = Decimal(str(point.total_value))
            if point.daily_change_percent is not None:
                result.append(Decimal(str(point.daily_change_percent)))
            elif previous is None or previous == 0:
                result.append(Decimal("0"))
            else:
                result.append((current - previous) / previous * Decimal("100"))
            previous = current

        return result

    @classmethod
    def calculate_metric_values(
        cls,
        history: list[PortfolioHistoryPoint],
        view: str,
    ) -> list[Decimal | None]:
        """Calculate the historical series for a supported history view."""
        if view in {"Portfolio Value", "Dollar Value"}:
            return [Decimal(str(point.total_value)) for point in history]

        if view in {"% Growth Since Start", "% Growth"}:
            return cls.calculate_growth_values(history)

        if view in {"Day's Gain/Loss", "Gain/Loss", "Daily Change"}:
            return cls.calculate_daily_change_values(history)

        if view in {"% Day's Gain/Loss", "% Daily Change"}:
            return cls.calculate_daily_change_percent_values(history)

        raise ValueError(f"Unsupported portfolio history view: {view}")

    @staticmethod
    def calculate_effective_date_range(
        requested_start: date,
        requested_end: date,
        history: list[PortfolioHistoryPoint],
    ) -> tuple[date, date] | None:
        """Return the date range actually represented by portfolio history."""
        if requested_start > requested_end or not history:
            return None

        effective_start = max(requested_start, history[0].snapshot_date)
        effective_end = min(requested_end, history[-1].snapshot_date)

        if effective_start > effective_end:
            return None

        return effective_start, effective_end

    @staticmethod
    def calculate_benchmark_growth(
        benchmark_history: list[BenchmarkHistoryPoint],
    ) -> list[Decimal]:
        """Normalize benchmark closes to percentage growth from the first close."""
        if not benchmark_history:
            return []

        first = Decimal(str(benchmark_history[0].value))
        if first == 0:
            return [Decimal("0") for _ in benchmark_history]

        return [
            (Decimal(str(point.value)) - first) / first * Decimal("100")
            for point in benchmark_history
        ]

    @staticmethod
    def calculate_benchmark_query_start(
        effective_start: date,
        daily_change_view: bool = False,
    ) -> date:
        """Return the benchmark download start needed for the selected view."""
        if daily_change_view:
            return effective_start - timedelta(days=14)
        return effective_start

    @staticmethod
    def calculate_benchmark_daily_change_percent_values(
        benchmark_history: list[BenchmarkHistoryPoint],
        previous_close: Decimal | None = None,
    ) -> list[Decimal]:
        """Calculate benchmark daily returns, optionally using a prior close."""
        if not benchmark_history:
            return []

        result: list[Decimal] = []
        previous = previous_close

        for point in benchmark_history:
            if previous is None or previous == 0:
                result.append(Decimal("0"))
            else:
                result.append(
                    (Decimal(str(point.value)) - previous)
                    / previous
                    * Decimal("100")
                )
            previous = Decimal(str(point.value))

        return result

    @staticmethod
    def filter_benchmark_history(
        benchmark_history: list[BenchmarkHistoryPoint],
        effective_start: date,
        effective_end: date,
    ) -> tuple[list[BenchmarkHistoryPoint], Decimal | None]:
        """Keep benchmark points in the effective range and return prior close."""
        previous_points = [
            point
            for point in benchmark_history
            if point.snapshot_date < effective_start
        ]
        filtered = [
            point
            for point in benchmark_history
            if effective_start <= point.snapshot_date <= effective_end
        ]
        previous_close = (
            previous_points[-1].value
            if previous_points
            else None
        )
        return filtered, previous_close

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
