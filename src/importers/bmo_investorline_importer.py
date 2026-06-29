"""
bmo_investorline_importer.py

Importer for BMO InvestorLine Excel portfolio exports.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from src.dto.imported_account import ImportedAccount
from src.dto.imported_cash import ImportedCash
from src.dto.imported_position import ImportedPosition
from src.importers.bmo_layout import BMOLayout
from src.importers.excel_reader import ExcelReader
from src.importers.worksheet_helper import WorksheetHelper


class BMOInvestorLineImporter:
    """
    Imports a BMO InvestorLine workbook.
    """

    def __init__(
        self,
        filename: str | Path,
    ) -> None:

        self._filename = Path(filename)

    @property
    def filename(self) -> Path:
        return self._filename

    def import_account(self) -> ImportedAccount:
        """
        Import the workbook.
        """

        with ExcelReader(self._filename) as reader:

            sheet = reader.first_worksheet

            layout = BMOLayout.discover(sheet)

            account = ImportedAccount(
                account_number=layout.account_number,
                account_name=f"BMO {layout.account_type}",
                account_type=layout.account_type,
                statement_date=layout.statement_date,
            )

            self._read_cash(
                sheet,
                layout,
                account,
            )

            self._read_positions(
                sheet,
                layout,
                account,
            )

            return account

    # ------------------------------------------------------------------

    def _read_cash(
        self,
        sheet: WorksheetHelper,
        layout: BMOLayout,
        account: ImportedAccount,
    ) -> None:

        row = layout.cash_data_row

        while row <= sheet.max_row:

            cash = self._read_cash_row(
                sheet,
                layout,
                row,
            )

            if cash is None:
                break

            account.cash.append(cash)

            row += 1

    # ------------------------------------------------------------------

    def _read_cash_row(
        self,
        sheet: WorksheetHelper,
        layout: BMOLayout,
        row: int,
    ) -> ImportedCash | None:

        currency = sheet.cell_text(
            row,
            layout.currency_column,
        )

        if not currency:
            return None

        if currency.lower().startswith("total"):
            return None

        amount = Decimal(
            str(
                sheet.cell_value(
                    row,
                    layout.cash_column,
                )
            )
        )

        return ImportedCash(
            currency=currency,
            amount=amount,
        )

    # ------------------------------------------------------------------

    def _read_positions(
        self,
        sheet: WorksheetHelper,
        layout: BMOLayout,
        account: ImportedAccount,
    ) -> None:

        row = layout.holdings_data_row

        while row <= sheet.max_row:

            position = self._read_position_row(
                sheet,
                layout,
                row,
            )

            if position is None:
                break

            account.positions.append(position)

            row += 1

    # ------------------------------------------------------------------

    def _read_position_row(
        self,
        sheet: WorksheetHelper,
        layout: BMOLayout,
        row: int,
    ) -> ImportedPosition | None:

        symbol = sheet.cell_text(
            row,
            layout.symbol_column,
        )

        if not symbol:
            return None

        return ImportedPosition(
            symbol=symbol,

            description=sheet.cell_text(
                row,
                layout.description_column,
            ),

            quantity=Decimal(
                str(
                    sheet.cell_value(
                        row,
                        layout.quantity_column,
                    )
                )
            ),

            unit_price=Decimal(
                str(
                    sheet.cell_value(
                        row,
                        layout.current_price_column,
                    )
                )
            ),

            market_value=Decimal(
                str(
                    sheet.cell_value(
                        row,
                        layout.market_value_column,
                    )
                )
            ),

            cost_basis=Decimal(
                str(
                    sheet.cell_value(
                        row,
                        layout.total_cost_column,
                    )
                )
            ),

            currency=sheet.cell_text(
                row,
                layout.settlement_currency_column,
            ),

            security_type=sheet.cell_text(
                row,
                layout.asset_class_column,
            ),
        )