"""
BMO InvestorLine Excel importer.

Reads a BMO portfolio Excel snapshot and extracts the account,
snapshot timestamp, cash balances, and security holdings.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
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

    def import_file(self) -> ImportedAccount:
        """Read the BMO Excel file and return its imported data."""
        workbook = load_workbook(
            filename=self.file_path,
            data_only=True,
        )

        if self.SHEET_NAME not in workbook.sheetnames:
            raise ValueError(
                f"Expected worksheet '{self.SHEET_NAME}' "
                f"was not found."
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

            currency_text = str(currency).strip()

            # BMO includes a summary row such as "Total (in CAD)".
            # Only actual CAD and USD cash balances are imported.
            if currency_text not in {"CAD", "USD"}:
                continue

            cash.append(
                ImportedCash(
                    currency=currency_text,
                    amount=Decimal(str(amount)),
                )
            )

        return cash

    @staticmethod
    def _parse_numeric_value(value: object) -> Decimal:
        """Parse a numeric value from an Excel cell.

        BMO sometimes returns values such as "65.39 C" or "13.27 U"
        for previous close, where the trailing letter identifies the
        currency. Only the numeric portion belongs in the database.
        """
        if value is None:
            return Decimal("0")

        if isinstance(value, (int, float, Decimal)):
            return Decimal(str(value))

        match = re.search(
            r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)",
            str(value),
        )

        if match is None:
            raise ValueError(
                f"Could not parse numeric value: {value!r}"
            )

        return Decimal(match.group(0))

    @staticmethod
    def _find_holdings_start_row(worksheet) -> int:
        """Find the first actual holding row below the Holding Details section.

        The BMO report layout can move, and openpyxl row insertion can leave
        structural/header artifacts behind. The importer therefore does not
        depend on either a fixed header row or a particular header candidate.
        It finds the section marker and then the first row containing the
        numeric fields that identify an actual holding.
        """
        holding_details_row = None

        for row in range(1, worksheet.max_row + 1):
            for col in range(1, min(worksheet.max_column, 10) + 1):
                value = worksheet.cell(row, col).value
                if (
                    isinstance(value, str)
                    and value.strip().lower() == "holding details"
                ):
                    holding_details_row = row
                    break
            if holding_details_row is not None:
                break

        if holding_details_row is None:
            raise ValueError(
                "Could not find 'Holding Details' section in BMO worksheet."
            )

        for row in range(holding_details_row + 1, worksheet.max_row + 1):
            symbol = worksheet.cell(row, 1).value
            quantity = worksheet.cell(row, 3).value
            market_value = worksheet.cell(row, 10).value

            if symbol is None or str(symbol).strip() == "":
                continue

            if (
                isinstance(symbol, str)
                and symbol.strip().lower().startswith("exchange rate")
            ):
                break

            if quantity is None or market_value is None:
                continue

            try:
                Decimal(str(quantity))
                Decimal(str(market_value))
            except (TypeError, ValueError, ArithmeticError):
                continue

            return row

        raise ValueError(
            "Could not find the first holding row below 'Holding Details'."
        )

    def _read_holdings(self, worksheet) -> list[ImportedHolding]:
        """Read security holdings from the dynamically located holdings section."""
        start_row = self._find_holdings_start_row(worksheet)
        holdings: list[ImportedHolding] = []

        for row in range(start_row, worksheet.max_row + 1):
            symbol = worksheet.cell(row, 1).value

            if symbol is None or str(symbol).strip() == "":
                # Blank rows inside the section are harmless. Continue looking
                # until the next explicit section marker.
                continue

            symbol = str(symbol).strip()

            if symbol.lower().startswith("exchange rate"):
                break

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

            try:
                holdings.append(
                    ImportedHolding(
                        symbol=symbol,
                        company_name=str(company_name or ""),
                        quantity=Decimal(str(quantity)),
                        average_cost=Decimal(str(average_cost or 0)),
                        price=Decimal(str(price or 0)),
                        market_value=Decimal(str(market_value)),
                        unrealized_gain=Decimal(str(unrealized_gain or 0)),
                        unrealized_gain_percent=Decimal(
                            str(unrealized_gain_percent or 0)
                        ),
                        daily_change=Decimal(str(daily_change or 0)),
                        daily_change_percent=Decimal(
                            str(daily_change_percent or 0)
                        ),
                        previous_close=self._parse_numeric_value(previous_close),
                        currency=str(currency or "CAD"),
                    )
                )
            except (TypeError, ValueError, ArithmeticError):
                continue

        return holdings

