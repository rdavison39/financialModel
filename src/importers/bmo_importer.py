"""
BMO InvestorLine Excel importer.

Reads a BMO portfolio Excel snapshot and extracts the account,
snapshot timestamp, cash balances, and security holdings.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re

from openpyxl import load_workbook


@dataclass
class ImportedCash:
    """Cash balance imported from a brokerage snapshot."""

    currency: str
    amount: Decimal


@dataclass
class ImportedHolding:
    """Security holding imported from a brokerage snapshot."""

    symbol: str
    company_name: str
    quantity: Decimal
    average_cost: Decimal
    price: Decimal
    market_value: Decimal
    unrealized_gain: Decimal
    unrealized_gain_percent: Decimal
    daily_change: Decimal
    daily_change_percent: Decimal
    previous_close: Decimal
    currency: str


@dataclass
class ImportedAccount:
    """Complete BMO account snapshot imported from Excel."""

    account_number: str
    snapshot_date: datetime
    cash: list[ImportedCash]
    holdings: list[ImportedHolding]


class BMOImporter:
    """Imports a BMO InvestorLine Excel portfolio report."""

    SHEET_NAME = "Holdings"

    def __init__(self, file_path: str | Path) -> None:
        """Initialize the importer."""
        self.file_path = Path(file_path)

    @staticmethod
    def _decimal_or_zero(value: object) -> Decimal:
        """Convert a numeric spreadsheet value to Decimal.

        Brokerage exports can contain text placeholders in optional
        numeric columns. Treat blank/non-numeric optional values as zero.
        """
        if value is None:
            return Decimal("0")

        if isinstance(value, Decimal):
            return value

        if isinstance(value, (int, float)):
            return Decimal(str(value))

        text = str(value).strip()

        if not text:
            return Decimal("0")

        try:
            return Decimal(text.replace(",", "").replace("$", "").strip())
        except InvalidOperation:
            return Decimal("0")

    def import_file(self) -> ImportedAccount:
        """Read the BMO Excel file and return its imported data."""
        workbook = load_workbook(
            filename=self.file_path,
            data_only=True,
        )

        if self.SHEET_NAME not in workbook.sheetnames:
            raise ValueError(
                f"Expected worksheet '{self.SHEET_NAME}' was not found."
            )

        worksheet = workbook[self.SHEET_NAME]

        account_number, snapshot_date = self._read_report_header(
            worksheet.cell(1, 6).value
        )

        cash = self._read_cash(worksheet)
        holdings = self._read_holdings(worksheet)

        return ImportedAccount(
            account_number=account_number,
            snapshot_date=snapshot_date,
            cash=cash,
            holdings=holdings,
        )

    def _read_report_header(
        self,
        header: object,
    ) -> tuple[str, datetime]:
        """Extract the account number and snapshot timestamp."""
        if not isinstance(header, str):
            raise ValueError("BMO report header is missing.")

        match = re.search(
            r"account\s*#\s*(\d+).*?as of\s+"
            r"(.+?)\s*\(Eastern Daylight Time\)",
            header,
            re.IGNORECASE,
        )

        if not match:
            raise ValueError(
                f"Could not parse BMO report header: {header}"
            )

        account_number = match.group(1)
        date_text = match.group(2).strip()

        snapshot_date = datetime.strptime(
            date_text,
            "%a %b %d %Y %H:%M:%S GMT-0400",
        )

        return account_number, snapshot_date

    def _read_cash(self, worksheet) -> list[ImportedCash]:
        """Read cash balances from the Cash Details section."""
        cash: list[ImportedCash] = []

        for row in range(4, 6):
            currency = worksheet.cell(row, 1).value
            amount = worksheet.cell(row, 3).value

            if currency is None or amount is None:
                continue

            cash.append(
                ImportedCash(
                    currency=str(currency),
                    amount=Decimal(str(amount)),
                )
            )

        return cash

    def _read_holdings(self, worksheet) -> list[ImportedHolding]:
        """Read security holdings from the Holding Details section."""
        holdings: list[ImportedHolding] = []

        for row in range(13, worksheet.max_row + 1):
            symbol = worksheet.cell(row, 1).value

            if not symbol:
                continue

            company_name = worksheet.cell(row, 2).value
            quantity = worksheet.cell(row, 3).value
            average_cost = worksheet.cell(row, 4).value
            price = worksheet.cell(row, 6).value
            market_value = worksheet.cell(row, 10).value
            currency = worksheet.cell(row, 11).value
            unrealized_gain = worksheet.cell(row, 12).value
            unrealized_gain_percent = worksheet.cell(row, 14).value
            daily_change = worksheet.cell(row, 22).value
            daily_change_percent = worksheet.cell(row, 23).value
            previous_close = worksheet.cell(row, 25).value

            if quantity is None or market_value is None:
                continue

            holdings.append(
                ImportedHolding(
                    symbol=str(symbol),
                    company_name=str(company_name or ""),
                    quantity=Decimal(str(quantity)),
                    average_cost=self._decimal_or_zero(average_cost),
                    price=self._decimal_or_zero(price),
                    market_value=Decimal(str(market_value)),
                    unrealized_gain=self._decimal_or_zero(unrealized_gain),
                    unrealized_gain_percent=self._decimal_or_zero(
                        unrealized_gain_percent
                    ),
                    daily_change=self._decimal_or_zero(daily_change),
                    daily_change_percent=self._decimal_or_zero(
                        daily_change_percent
                    ),
                    previous_close=self._decimal_or_zero(previous_close),
                    currency=str(currency or "CAD"),
                )
            )

        return holdings
