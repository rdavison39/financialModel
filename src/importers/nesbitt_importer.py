"""
Importer for Nesbitt Burns portfolio Excel reports.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from openpyxl import load_workbook


@dataclass
class ImportedCash:
    """Cash imported from a brokerage report."""

    currency: str
    amount: Decimal


@dataclass
class ImportedHolding:
    """Holding imported from a brokerage report."""

    symbol: str
    company_name: str
    quantity: Decimal
    price: Decimal
    market_value: Decimal
    currency: str


@dataclass
class ImportedAccount:
    """Account snapshot imported from a brokerage report."""

    account_number: str
    snapshot_date: datetime
    cash: list[ImportedCash]
    holdings: list[ImportedHolding]


class NesbittImporter:
    """Imports a Nesbitt Burns portfolio report."""

    def __init__(self, file_path: str | Path) -> None:
        """Initialize the importer."""

        self.file_path = Path(file_path)

    def import_file(self) -> ImportedAccount:
        """Import the Nesbitt Burns Excel report."""

        workbook = load_workbook(
            filename=self.file_path,
            data_only=True,
        )

        worksheet = workbook["Holdings"]

        account_number, snapshot_date = self._parse_header(
            worksheet["F1"].value,
        )

        cash = self._parse_cash(worksheet)
        holdings = self._parse_holdings(worksheet)

        return ImportedAccount(
            account_number=account_number,
            snapshot_date=snapshot_date,
            cash=cash,
            holdings=holdings,
        )

    def _parse_header(
        self,
        header: str | None,
    ) -> tuple[str, datetime]:
        """Parse account number and snapshot date."""

        if not header:
            raise ValueError(
                "Nesbitt Burns report header is missing."
            )

        account_match = re.search(
            r"account\s*#\s*(\d+)",
            str(header),
            re.IGNORECASE,
        )

        if account_match is None:
            raise ValueError(
                f"Could not parse Nesbitt Burns account number: {header}"
            )

        account_number = account_match.group(1)

        timestamp_match = re.search(
            r"as of\s+(.+)$",
            str(header),
            re.IGNORECASE,
        )

        if timestamp_match and timestamp_match.group(1).strip():
            timestamp_text = timestamp_match.group(1).strip()

            try:
                snapshot_date = datetime.fromisoformat(
                    timestamp_text
                )
            except ValueError as exc:
                raise ValueError(
                    "Could not parse Nesbitt Burns report timestamp: "
                    f"{timestamp_text}"
                ) from exc
        else:
            snapshot_date = datetime.fromtimestamp(
                self.file_path.stat().st_mtime
            )

        return account_number, snapshot_date

    def _parse_cash(self, worksheet) -> list[ImportedCash]:
        """Parse cash balances from the cash details section."""

        cash: list[ImportedCash] = []

        for row in range(4, 7):
            currency = worksheet.cell(
                row=row,
                column=1,
            ).value

            amount = worksheet.cell(
                row=row,
                column=3,
            ).value

            if currency is None or amount is None:
                continue

            currency_text = str(currency).strip()

            if currency_text.startswith("Total"):
                continue

            cash.append(
                ImportedCash(
                    currency=currency_text,
                    amount=Decimal(str(amount)),
                )
            )

        return cash

    def _parse_holdings(self, worksheet) -> list[ImportedHolding]:
        """Parse security holdings from the report."""

        holdings: list[ImportedHolding] = []

        for row in range(13, worksheet.max_row + 1):
            symbol = worksheet.cell(
                row=row,
                column=1,
            ).value

            description = worksheet.cell(
                row=row,
                column=2,
            ).value

            quantity = worksheet.cell(
                row=row,
                column=4,
            ).value

            price = worksheet.cell(
                row=row,
                column=7,
            ).value

            market_value = worksheet.cell(
                row=row,
                column=11,
            ).value

            currency = worksheet.cell(
                row=row,
                column=12,
            ).value

            if symbol is None:
                continue

            symbol_text = str(symbol).strip()

            if symbol_text in {
                "CANADIAN DOLLAR",
                "US DOLLAR",
            }:
                continue

            if quantity is None or price is None or market_value is None:
                continue

            holdings.append(
                ImportedHolding(
                    symbol=symbol_text,
                    company_name=(
                        str(description).strip()
                        if description is not None
                        else symbol_text
                    ),
                    quantity=Decimal(str(quantity)),
                    price=Decimal(str(price)),
                    market_value=Decimal(str(market_value)),
                    currency=(
                        str(currency).strip()
                        if currency is not None
                        else "CAD"
                    ),
                )
            )

        return holdings