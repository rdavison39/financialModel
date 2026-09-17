"""
Service for retrieving current market prices from Yahoo Finance.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, time
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
        Retrieve the current price and daily change for a symbol.

        During regular market hours, the latest regular-session intraday
        price is used.

        After the market closes, today's official daily close is preferred.
        Yahoo sometimes creates today's daily row before populating its
        Close value. In that case, the last available regular-session
        one-minute bar is used as the fallback.

        If Yahoo has no usable price for a security, try alternate Yahoo
        symbols before returning an unavailable MarketPrice. The portfolio
        valuation service can then fall back to the brokerage-imported price.
        """
        yahoo_symbols = self._yahoo_symbol_candidates(symbol)

        for yahoo_symbol in yahoo_symbols:
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

                previous_close = self._previous_close(
                    daily_rows,
                    today,
                )
                today_close = self._close_for_date(
                    daily_rows,
                    today,
                )

                intraday_history = ticker.history(
                    period="1d",
                    interval="1m",
                )

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
                        f"  WARNING: No current price for {symbol} "
                        f"using {yahoo_symbol}"
                    )
                    continue

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
                # Some securities, particularly Canadian preferred shares,
                # may not have usable Yahoo data under one ticker format.
                # Try the next candidate before giving up.
                logger.debug(
                    "Unable to retrieve price for %s using %s: %s",
                    symbol,
                    yahoo_symbol,
                    exc,
                )

                self._report_progress(
                    f"  WARNING: Yahoo price unavailable for "
                    f"{symbol} using {yahoo_symbol}"
                )

        self._report_progress(
            f"  WARNING: Yahoo price unavailable for {symbol}"
        )
        return self._unavailable()

    @staticmethod
    def _yahoo_symbol_candidates(symbol: str) -> list[str]:
        """Return Yahoo Finance symbols to try for a brokerage symbol."""
        candidates: list[str] = []

        normal_symbol = MarketPriceService._convert_symbol(symbol)
        candidates.append(normal_symbol)

        preferred_symbol = (
            MarketPriceService._convert_preferred_share_symbol(symbol)
        )
        if preferred_symbol is not None and preferred_symbol not in candidates:
            candidates.append(preferred_symbol)

        mapped_symbol = YAHOO_SYMBOL_MAP.get(symbol)
        if mapped_symbol is not None and mapped_symbol not in candidates:
            candidates.append(mapped_symbol)

        return candidates

    @staticmethod
    def _convert_preferred_share_symbol(symbol: str) -> str | None:
        """
        Convert a Canadian preferred-share brokerage symbol to Yahoo format.

        Examples:
            BPO.PR.N:CA -> BPO-PN.TO
            BCE.PR.M:CA -> BCE-PM.TO

        Return None when the symbol does not match this pattern.
        """
        normalized = symbol.strip().upper()

        match = re.fullmatch(
            r"([A-Z0-9]+)\.PR\.([A-Z]):CA",
            normalized,
        )
        if match is None:
            return None

        issuer, series = match.groups()
        return f"{issuer}-P{series}.TO"

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
        """Convert brokerage symbols to Yahoo Finance symbols."""
        if symbol in YAHOO_SYMBOL_MAP:
            return YAHOO_SYMBOL_MAP[symbol]

        if symbol.endswith(":CA"):
            return (
                symbol[:-3].replace(".", "-")
                + ".TO"
            )

        if symbol.endswith(":US"):
            return symbol[:-3]

        return symbol