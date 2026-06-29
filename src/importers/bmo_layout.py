"""
bmo_layout.py

Discovers the layout of a BMO InvestorLine workbook.

This class is responsible for locating sections, column headings,
and parsing account information from the worksheet.

The importer should never search the worksheet directly. Instead it
should ask BMOLayout where each piece of information resides.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime

from src.importers import bmo_constants as c
from src.importers.worksheet_helper import WorksheetHelper


@dataclass(frozen=True, slots=True)
class BMOLayout:
    """
    Describes the layout of a BMO InvestorLine worksheet.
    """

    account_number: str
    account_type: str
    statement_date: date

    cash_header_row: int
    cash_data_row: int

    holdings_header_row: int
    holdings_data_row: int

    currency_column: int
    cash_column: int

    symbol_column: int
    description_column: int
    quantity_column: int
    current_price_column: int
    total_cost_column: int
    market_value_column: int
    settlement_currency_column: int
    asset_class_column: int

    @classmethod
    def discover(
        cls,
        sheet: WorksheetHelper,
    ) -> "BMOLayout":
        """
        Discover the worksheet layout.
        """

        #
        # ------------------------------------------------------------------
        # Portfolio title
        # ------------------------------------------------------------------
        #

        location = sheet.find_text(
            c.PORTFOLIO_TITLE_PREFIX,
            case_sensitive=False,
        )

        if location is None:
            raise ValueError(
                "Portfolio title not found."
            )

        title_row, title_col = location

        title = sheet.cell_text(
            title_row,
            title_col,
        )

        match = re.search(
            (
                r"Portfolio report for "
                r"(.+?) account #\s*(\d+)"
                r"\s+as of\s+(.+?)\s+GMT"
            ),
            title,
            re.IGNORECASE,
        )

        if match is None:
            raise ValueError(
                "Unable to parse portfolio title."
            )

        account_type = match.group(1).strip()

        account_number = match.group(2).strip()

        statement_date = datetime.strptime(
            match.group(3).strip(),
            "%a %b %d %Y %H:%M:%S",
        ).date()

        #
        # ------------------------------------------------------------------
        # Cash section
        # ------------------------------------------------------------------
        #

        cash_row, _ = cls._find_required_text(
            sheet,
            c.CASH_DETAILS,
        )

        cash_header = cash_row + 1

        currency_column = cls._find_required_column(
            sheet,
            cash_header,
            c.CASH_COLUMN_CURRENCY,
        )

        cash_column = cls._find_required_column(
            sheet,
            cash_header,
            c.CASH_COLUMN_CASH,
        )

        #
        # ------------------------------------------------------------------
        # Holdings section
        # ------------------------------------------------------------------
        #

        holdings_row, _ = cls._find_required_text(
            sheet,
            c.HOLDING_DETAILS,
        )

        holdings_header = holdings_row + 1

        return cls(
            account_number=account_number,
            account_type=account_type,
            statement_date=statement_date,

            cash_header_row=cash_header,
            cash_data_row=cash_header + 1,

            holdings_header_row=holdings_header,
            holdings_data_row=holdings_header + 1,

            currency_column=currency_column,
            cash_column=cash_column,

            symbol_column=cls._find_required_column(
                sheet,
                holdings_header,
                c.COLUMN_SYMBOL,
            ),

            description_column=cls._find_required_column(
                sheet,
                holdings_header,
                c.COLUMN_DESCRIPTION,
            ),

            quantity_column=cls._find_required_column(
                sheet,
                holdings_header,
                c.COLUMN_QUANTITY,
            ),

            current_price_column=cls._find_required_column(
                sheet,
                holdings_header,
                c.COLUMN_CURRENT_PRICE,
            ),

            total_cost_column=cls._find_required_column(
                sheet,
                holdings_header,
                c.COLUMN_TOTAL_COST,
            ),

            market_value_column=cls._find_required_column(
                sheet,
                holdings_header,
                c.COLUMN_MARKET_VALUE,
            ),

            settlement_currency_column=cls._find_required_column(
                sheet,
                holdings_header,
                c.COLUMN_SETTLEMENT_CURRENCY,
            ),

            asset_class_column=cls._find_required_column(
                sheet,
                holdings_header,
                c.COLUMN_ASSET_CLASS,
            ),
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _find_required_text(
        sheet: WorksheetHelper,
        text: str,
    ) -> tuple[int, int]:

        location = sheet.find_text(
            text,
            case_sensitive=False,
        )

        if location is None:
            raise ValueError(
                f"'{text}' not found."
            )

        return location

    # ------------------------------------------------------------------

    @staticmethod
    def _find_required_column(
        sheet: WorksheetHelper,
        row: int,
        heading: str,
    ) -> int:

        column = sheet.find_text_in_row(
            heading,
            row,
            case_sensitive=False,
        )

        if column is None:
            raise ValueError(
                f"Column '{heading}' not found."
            )

        return column