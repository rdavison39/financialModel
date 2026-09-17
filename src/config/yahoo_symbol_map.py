"""
Explicit mappings for brokerage symbols that differ from Yahoo Finance symbols.

Most Canadian preferred shares are handled algorithmically by
MarketPriceService. Keep only genuine exceptions here.
"""

YAHOO_SYMBOL_MAP: dict[str, str] = {}
