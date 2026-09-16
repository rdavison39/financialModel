"""
Service for retrieving current market prices from Yahoo Finance.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

import yfinance as yf

from src.config.yahoo_symbol_map import YAHOO_SYMBOL_MAP

logger = logging.getLogger(__name__)


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

        logging.getLogger("yfinance").setLevel(logging.CRITICAL)

    def get_price(self, symbol: str) -> MarketPrice:
        """
        Retrieve the current price and daily change for a symbol.

        Returns:
            MarketPrice containing:
                - current price
                - previous close
                - dollar change
                - percentage change
                - whether the current price was successfully retrieved
        """

        yahoo_symbol = self._convert_symbol(symbol)

        self._report_progress(
            f"Getting price: {symbol} -> {yahoo_symbol}"
        )

        try:
            ticker = yf.Ticker(yahoo_symbol)

            # Get today's intraday price.
            history = ticker.history(
                period="1d",
                interval="1m",
            )

            if history.empty:
                self._report_progress(
                    f"  WARNING: No current price for {symbol}"
                )
                return self._unavailable()

            prices = history["Close"].dropna()

            if prices.empty:
                self._report_progress(
                    f"  WARNING: No current price for {symbol}"
                )
                return self._unavailable()

            current_price = Decimal(
                str(prices.iloc[-1])
            )

            # Get the previous daily close.
            daily_history = ticker.history(
                period="5d",
                interval="1d",
            )

            previous_close = Decimal("0")

            if not daily_history.empty:
                closes = daily_history["Close"].dropna()

                if len(closes) >= 2:
                    previous_close = Decimal(
                        str(closes.iloc[-2])
                    )
                elif len(closes) == 1:
                    previous_close = Decimal(
                        str(closes.iloc[-1])
                    )

            # Calculate daily dollar change.
            if previous_close != 0:
                change = current_price - previous_close
            else:
                change = Decimal("0")

            # Calculate daily percentage change.
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
            logger.debug(
                "Unable to retrieve price for %s: %s",
                symbol,
                exc,
            )

            self._report_progress(
                f"  WARNING: Yahoo price unavailable for {symbol}"
            )

            return self._unavailable()

    def _report_progress(self, message: str) -> None:
        """Send a progress message to the caller."""

        if self.progress_callback is not None:
            self.progress_callback(message)

    @staticmethod
    def _unavailable() -> MarketPrice:
        """Return an unavailable market price."""

        return MarketPrice(
            price=Decimal("0"),
            previous_close=Decimal("0"),
            change=Decimal("0"),
            change_percent=Decimal("0"),
            is_current=False,
        )

    def _convert_symbol(self, symbol: str) -> str:
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