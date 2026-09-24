"""
Service for retrieving current market prices from Yahoo Finance.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

import yfinance as yf

from src.config.yahoo_symbol_map import YAHOO_SYMBOL_MAP


logger = logging.getLogger(__name__)

EASTERN = ZoneInfo("America/New_York")
MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(16, 0)


@dataclass
class MarketPrice:
    """A market price and its daily change."""

    price: Decimal
    previous_close: Decimal
    change: Decimal
    change_percent: Decimal
    is_current: bool


class MarketPriceService:
    """Retrieves current security prices from Yahoo Finance."""

    def __init__(
        self,
        progress_callback: Callable[[str], None] | None = None,
    ) -> None:
        self.progress_callback = progress_callback

        # Keep yfinance quiet during a portfolio update.
        logging.getLogger("yfinance").setLevel(logging.CRITICAL)

    def get_price(self, symbol: str) -> MarketPrice:
        """
        Retrieve the current price and daily change for a brokerage symbol.

        Yahoo symbol conversion is attempted in this order:

        1. Normal Canadian/US conversion.
        2. Algorithmic Canadian preferred-share conversion.
        3. Explicit exception mapping.

        If Yahoo cannot provide usable data for one candidate, the next
        candidate is tried. This is important for Canadian preferred shares,
        where Yahoo can recognize one symbol form but not another.
        """
        candidates = self._yahoo_symbol_candidates(symbol)

        for yahoo_symbol in candidates:
            result = self._get_price_for_yahoo_symbol(
                symbol,
                yahoo_symbol,
            )

            if result.is_current:
                return result

        self._report_progress(
            f"  WARNING: Yahoo price unavailable for {symbol}"
        )
        return self._unavailable()

    def _get_price_for_yahoo_symbol(
        self,
        symbol: str,
        yahoo_symbol: str,
    ) -> MarketPrice:
        """
        Retrieve the current price and daily change for a symbol.

        During regular market hours, the latest regular-session intraday
        price is used.

        After the market closes, today's official daily close is preferred.
        Yahoo sometimes creates today's daily row before populating its
        Close value. In that case, the last available regular-session
        one-minute bar is used as the fallback.

        If Yahoo has no usable price for a security, return an unavailable
        MarketPrice rather than raising an exception. The portfolio valuation
        service can then fall back to the brokerage-imported price.
        """
        self._report_progress(
            f"Getting price: {symbol} -> {yahoo_symbol}"
        )

        try:
            # FX is effectively a 24/5 market, so use its own logic.
            if yahoo_symbol.upper() == "CAD=X":
                return self._get_fx_price(yahoo_symbol)

            ticker = yf.Ticker(yahoo_symbol)

            now_et = datetime.now(EASTERN)
            today = now_et.date()

            daily_history = ticker.history(
                period="10d",
                interval="1d",
            )
            daily_rows = self._daily_rows(daily_history)

            # Yahoo can occasionally omit a recent daily bar.  If that
            # happens, retry the recent window before calculating the daily
            # change so that a missing yesterday bar cannot turn a one-day
            # move into a two-day move.
            if self._needs_daily_history_retry(daily_rows, today):
                try:
                    retry_history = ticker.history(
                        start=(today - timedelta(days=5)).isoformat(),
                        end=(today + timedelta(days=1)).isoformat(),
                        interval="1d",
                    )
                    daily_rows = self._merge_daily_rows(
                        daily_rows,
                        self._daily_rows(retry_history),
                    )
                except Exception as exc:
                    logger.debug(
                        "Recent daily Yahoo retry unavailable for %s: %s",
                        yahoo_symbol,
                        exc,
                    )

            previous_close = self._previous_close(
                daily_rows,
                today,
            )

            # The Yahoo quote metadata exposes the previous official close.
            # For the TSX index, prefer it when available because it avoids
            # relying on the completeness of Yahoo's recent daily-history
            # rows.  Fall back to the history-derived value if metadata is
            # unavailable.
            if yahoo_symbol.upper() == "^GSPTSE":
                metadata_previous_close = self._quote_previous_close(ticker)
                if metadata_previous_close is not None:
                    previous_close = metadata_previous_close

            today_close = self._close_for_date(
                daily_rows,
                today,
            )

            # Some Canadian preferred shares have no usable Yahoo
            # one-minute history even though their daily history is valid.
            # Treat intraday data as optional so a valid daily close can
            # still be used.
            try:
                intraday_history = ticker.history(
                    period="1d",
                    interval="1m",
                )
            except Exception as exc:
                logger.debug(
                    "Intraday Yahoo data unavailable for %s: %s",
                    yahoo_symbol,
                    exc,
                )
                intraday_history = None

            session_price = self._today_regular_session_price(
                intraday_history,
                today,
            )

            market_is_open = (
                now_et.weekday() < 5
                and MARKET_OPEN
                <= now_et.time().replace(tzinfo=None)
                < MARKET_CLOSE
            )

            if market_is_open:
                current_price = session_price

                if current_price is None:
                    current_price = today_close
            else:
                # After the regular session, prefer the official daily
                # close. Yahoo may temporarily leave today's Close as NaN.
                if today_close is not None:
                    current_price = today_close
                else:
                    current_price = session_price

            # Weekend/holiday/pre-open fallback.
            if current_price is None:
                current_price = self._latest_daily_close(
                    daily_rows
                )

            if current_price is None:
                self._report_progress(
                    f"  WARNING: No current price for {symbol}"
                )
                return self._unavailable()

            if previous_close is None:
                previous_close = Decimal("0")

            change = current_price - previous_close

            if previous_close != 0:
                change_percent = (
                    change / previous_close
                ) * Decimal("100")
            else:
                change_percent = Decimal("0")

            self._report_progress(
                f"  OK: {current_price} "
                f"(today: {change:+.2f}, "
                f"{change_percent:+.2f}%)"
            )

            return MarketPrice(
                price=current_price,
                previous_close=previous_close,
                change=change,
                change_percent=change_percent,
                is_current=True,
            )

        except Exception as exc:
            # Some securities in the portfolio, particularly Canadian
            # preferred shares, may not have usable Yahoo intraday data.
            # Do not abort the entire portfolio update.
            logger.debug(
                "Unable to retrieve price for %s: %s",
                symbol,
                exc,
            )

            self._report_progress(
                f"  WARNING: Yahoo price unavailable for "
                f"{symbol} via {yahoo_symbol}"
            )

            return self._unavailable()

    def _get_fx_price(self, yahoo_symbol: str) -> MarketPrice:
        """Retrieve the current USD/CAD exchange rate."""
        ticker = yf.Ticker(yahoo_symbol)

        history = ticker.history(
            period="5d",
            interval="1h",
        )

        if history.empty:
            history = ticker.history(
                period="5d",
                interval="1d",
            )

        prices = (
            history["Close"].dropna()
            if not history.empty
            else None
        )

        if prices is None or prices.empty:
            raise ValueError(
                f"No FX price available for {yahoo_symbol}"
            )

        current_price = Decimal(str(prices.iloc[-1]))

        daily_history = ticker.history(
            period="10d",
            interval="1d",
        )
        daily_rows = self._daily_rows(daily_history)

        previous_close = (
            daily_rows[-2][1]
            if len(daily_rows) >= 2
            else Decimal("0")
        )

        change = current_price - previous_close

        if previous_close != 0:
            change_percent = (
                change / previous_close
            ) * Decimal("100")
        else:
            change_percent = Decimal("0")

        return MarketPrice(
            price=current_price,
            previous_close=previous_close,
            change=change,
            change_percent=change_percent,
            is_current=True,
        )

    def _report_progress(self, message: str) -> None:
        """Send a progress message to the caller."""
        if self.progress_callback is not None:
            self.progress_callback(message)

    @staticmethod
    def _unavailable() -> MarketPrice:
        """Return a price object indicating that Yahoo data is unavailable."""
        return MarketPrice(
            price=Decimal("0"),
            previous_close=Decimal("0"),
            change=Decimal("0"),
            change_percent=Decimal("0"),
            is_current=False,
        )

    @staticmethod
    def _daily_rows(history) -> list[tuple]:
        """
        Return valid daily rows as (ET date, Decimal close).

        Yahoo can return today's row with a NaN Close. Those rows are
        deliberately excluded.
        """
        if (
            history is None
            or history.empty
            or "Close" not in history.columns
        ):
            return []

        rows: list[tuple] = []

        for timestamp, row in history.iterrows():
            close = row["Close"]

            try:
                if close != close:  # NaN
                    continue

                close_decimal = Decimal(str(close))

            except (
                InvalidOperation,
                TypeError,
                ValueError,
            ):
                continue

            if close_decimal.is_nan():
                continue

            if getattr(timestamp, "tzinfo", None) is not None:
                date_value = timestamp.astimezone(
                    EASTERN
                ).date()
            else:
                date_value = timestamp.date()

            rows.append(
                (
                    date_value,
                    close_decimal,
                )
            )

        rows.sort(key=lambda item: item[0])
        return rows

    @staticmethod
    def _needs_daily_history_retry(
        daily_rows: list[tuple],
        target_date,
    ) -> bool:
        """Return True when recent daily history may be missing a bar."""
        if not daily_rows:
            return True

        latest_date = daily_rows[-1][0]

        if latest_date < target_date:
            return True

        if latest_date == target_date:
            if len(daily_rows) < 2:
                return True

            # A normal weekday immediately before today's trading session
            # should be represented by the prior row.  Weekends/holidays are
            # harmless because the retry simply supplies whatever trading
            # days actually exist.
            if target_date.weekday() < 5:
                prior_date = daily_rows[-2][0]
                if prior_date < target_date - timedelta(days=1):
                    return True

        return False

    @staticmethod
    def _merge_daily_rows(
        first_rows: list[tuple],
        second_rows: list[tuple],
    ) -> list[tuple]:
        """Merge daily rows by date, preferring the retry result."""
        merged = {row_date: close for row_date, close in first_rows}
        merged.update(
            {row_date: close for row_date, close in second_rows}
        )
        return sorted(merged.items(), key=lambda item: item[0])

    @staticmethod
    def _quote_previous_close(ticker) -> Decimal | None:
        """Return Yahoo's quote-level previous close when available."""
        try:
            info = ticker.info
            value = info.get("previousClose")
            if value is None:
                value = info.get("regularMarketPreviousClose")
            if value is None:
                return None

            result = Decimal(str(value))
            if result.is_nan() or result <= 0:
                return None
            return result
        except Exception:
            return None

    @staticmethod
    def _close_for_date(
        daily_rows: list[tuple],
        target_date,
    ) -> Decimal | None:
        """Return the daily close for target_date, if available."""
        for row_date, close in daily_rows:
            if row_date == target_date:
                return close

        return None

    @staticmethod
    def _previous_close(
        daily_rows: list[tuple],
        target_date,
    ) -> Decimal | None:
        """Return the close from the most recent prior trading day."""
        prior = [
            close
            for row_date, close in daily_rows
            if row_date < target_date
        ]

        if not prior:
            return None

        return prior[-1]

    @staticmethod
    def _latest_daily_close(
        daily_rows: list[tuple],
    ) -> Decimal | None:
        """Return the most recent valid daily close."""
        if not daily_rows:
            return None

        return daily_rows[-1][1]

    @staticmethod
    def _today_regular_session_price(
        history,
        target_date,
    ) -> Decimal | None:
        """
        Return the final available regular-session intraday close.

        We intentionally do not require exactly 15:59 because Yahoo can
        omit individual minute bars.
        """
        if (
            history is None
            or history.empty
            or "Close" not in history.columns
        ):
            return None

        latest_price: Decimal | None = None

        for timestamp, row in history.iterrows():
            close = row["Close"]

            try:
                if close != close:  # NaN
                    continue

                close_decimal = Decimal(str(close))

            except (
                InvalidOperation,
                TypeError,
                ValueError,
            ):
                continue

            if close_decimal.is_nan():
                continue

            if getattr(timestamp, "tzinfo", None) is not None:
                et_timestamp = timestamp.astimezone(
                    EASTERN
                )
            else:
                et_timestamp = timestamp.replace(
                    tzinfo=EASTERN
                )

            if et_timestamp.date() != target_date:
                continue

            bar_time = et_timestamp.time().replace(
                tzinfo=None
            )

            if (
                MARKET_OPEN
                <= bar_time
                < MARKET_CLOSE
            ):
                latest_price = close_decimal

        return latest_price

    @staticmethod
    def _convert_symbol(symbol: str) -> str:
        """Apply the normal brokerage-to-Yahoo symbol conversion."""
        if symbol.endswith(":CA"):
            return (
                symbol[:-3].replace(".", "-")
                + ".TO"
            )

        if symbol.endswith(":US"):
            return symbol[:-3]

        return symbol

    @staticmethod
    def _convert_preferred_share_symbol(
        symbol: str,
    ) -> str | None:
        """
        Convert a Canadian brokerage preferred-share symbol algorithmically.

        Examples:
            BPO.PR.A:CA -> BPO-PA.TO
            BCE.PR.M:CA -> BCE-PM.TO
        """
        if not symbol.endswith(":CA"):
            return None

        base = symbol[:-3]

        parts = base.split(".PR.")
        if len(parts) != 2:
            return None

        issuer, series = parts
        if not issuer or not series:
            return None

        return f"{issuer}-P{series}.TO"

    @classmethod
    def _yahoo_symbol_candidates(
        cls,
        symbol: str,
    ) -> list[str]:
        """Return Yahoo symbols to try, in preferred lookup order."""
        candidates: list[str] = []

        def add(candidate: str | None) -> None:
            if candidate and candidate not in candidates:
                candidates.append(candidate)

        # 1. Normal conversion.
        add(cls._convert_symbol(symbol))

        # 2. Algorithmic Canadian preferred-share conversion.
        add(cls._convert_preferred_share_symbol(symbol))

        # 3. Explicit exceptions.
        add(YAHOO_SYMBOL_MAP.get(symbol))

        return candidates
