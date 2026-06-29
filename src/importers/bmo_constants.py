"""
bmo_constants.py

Constants used by the BMO InvestorLine importer.

Keeping all worksheet labels in one place makes the importer easier
to read and isolates future BMO worksheet changes to a single file.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

# ----------------------------------------------------------------------
# Worksheet
# ----------------------------------------------------------------------

WORKSHEET_NAME = "Holdings"

# ----------------------------------------------------------------------
# Workbook title
# ----------------------------------------------------------------------

PORTFOLIO_TITLE_PREFIX = "Portfolio report for"

# ----------------------------------------------------------------------
# Section headings
# ----------------------------------------------------------------------

CASH_DETAILS = "Cash Details"
HOLDING_DETAILS = "Holding Details"

# ----------------------------------------------------------------------
# Cash table columns
# ----------------------------------------------------------------------

CASH_COLUMN_CURRENCY = "Currency"
CASH_COLUMN_CASH = "Cash"

# ----------------------------------------------------------------------
# Holdings table columns
# ----------------------------------------------------------------------

COLUMN_SYMBOL = "Symbol"

COLUMN_DESCRIPTION = "Security Description"

COLUMN_QUANTITY = "Quantity"

COLUMN_CURRENT_PRICE = "Current price"

COLUMN_TOTAL_COST = "Total cost"

COLUMN_MARKET_VALUE = "Market Value"

COLUMN_SETTLEMENT_CURRENCY = "Settlement Currency"

COLUMN_ASSET_CLASS = "Asset Class"

# ----------------------------------------------------------------------
# Common values
# ----------------------------------------------------------------------

CAD = "CAD"

USD = "USD"

SUPPORTED_CURRENCIES = (
    CAD,
    USD,
)