"""
Service for retrieving current market prices from Yahoo Finance.
"""

from dataclasses import dataclass
from decimal import Decimal

import yfinance as yf

from src.config.yahoo_symbol_map import YAHOO_SYMBOL_MAP


@dataclass
class MarketPrice:
    """A market price and its source."""

    price: Decimal
    is_current: bool


class MarketPriceService:
    """Retrieves current security prices from Yahoo Finance."""

    def get_price(self, symbol: str) -> MarketPrice:
        """Return the current market price from Yahoo Finance."""

        yahoo_symbol = self._convert_symbol(symbol)

        ticker = yf.Ticker(yahoo_symbol)

        history = ticker.history(
            period="1d",
            interval="1m",
        )

        if history.empty:
            return MarketPrice(
                price=Decimal("0"),
                is_current=False,
            )

        prices = history["Close"].dropna()

        if prices.empty:
            return MarketPrice(
                price=Decimal("0"),
                is_current=False,
            )

        return MarketPrice(
            price=Decimal(str(prices.iloc[-1])),
            is_current=True,
        )

    def _convert_symbol(self, symbol: str) -> str:
        """Convert a brokerage symbol to a Yahoo Finance symbol."""

        if symbol in YAHOO_SYMBOL_MAP:
            return YAHOO_SYMBOL_MAP[symbol]

        if symbol.endswith(":CA"):
            return symbol[:-3].replace(".", "-") + ".TO"

        if symbol.endswith(":US"):
            return symbol[:-3]

        return symbol