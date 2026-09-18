"""
Export included investment accounts to CSV files.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.account import Account
from src.models.brokerage import Brokerage
from src.models.portfolio_snapshot import PortfolioSnapshot
from src.services.portfolio_valuation_service import (
    CurrentCash,
    CurrentHolding,
    PortfolioValuationService,
)


@dataclass(frozen=True)
class ExportAccount:
    """Account metadata used in an export."""

    account_id: int
    brokerage: str
    account_number: str
    name: str
    account_type: str


class AccountExportService:
    """Export included accounts using the latest saved portfolio valuation."""

    HEADERS = (
        "Record Type",
        "Brokerage",
        "Account Number",
        "Account Name",
        "Account Type",
        "Valuation Date",
        "Valuation Updated At",
        "Symbol",
        "Company Name",
        "Quantity",
        "Currency",
        "Average Cost",
        "Unrealized Gain",
        "Unrealized Gain %",
        "Previous Close",
        "Current Price",
        "Daily Change",
        "Daily Change %",
        "Current Value (CAD)",
        "Is Current",
        "Cash Amount",
    )

    def __init__(self, session: Session) -> None:
        self.session = session
        self.valuation_service = PortfolioValuationService(session)

    def export_included_accounts(self, output_directory: Path) -> list[Path]:
        """
        Export every included account and, when appropriate, a combined file.

        One CSV is created for every account whose Include setting is checked.
        If more than one account is included, ``All_Accounts.csv`` is also
        created.  The combined file contains the same rows as the individual
        account files and repeats the account metadata on every row.
        """
        output_directory = Path(output_directory)
        output_directory.mkdir(parents=True, exist_ok=True)

        accounts = self._get_included_accounts()
        if not accounts:
            raise ValueError("No accounts are marked Include in Portfolio.")

        exported_paths: list[Path] = []
        all_rows: list[dict[str, str]] = []

        for account in accounts:
            rows = self._build_account_rows(account)
            path = output_directory / self._account_filename(account)
            self._write_csv(path, rows)
            exported_paths.append(path)
            all_rows.extend(rows)

        if len(accounts) > 1:
            summary_path = output_directory / "All_Accounts.csv"
            self._write_csv(summary_path, all_rows)
            exported_paths.append(summary_path)

        return exported_paths

    def _get_included_accounts(self) -> list[ExportAccount]:
        rows = self.session.execute(
            select(Account, Brokerage)
            .join(Brokerage, Brokerage.id == Account.brokerage_id)
            .where(Account.include_in_portfolio.is_(True))
            .order_by(Brokerage.name, Account.account_number)
        ).all()

        return [
            ExportAccount(
                account_id=account.id,
                brokerage=brokerage.name,
                account_number=account.account_number,
                name=account.name,
                account_type=account.account_type or "",
            )
            for account, brokerage in rows
        ]

    def _build_account_rows(
        self,
        account: ExportAccount,
    ) -> list[dict[str, str]]:
        snapshot = self.session.scalar(
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.account_id == account.account_id)
            .order_by(
                PortfolioSnapshot.snapshot_date.desc(),
                PortfolioSnapshot.id.desc(),
            )
            .limit(1)
        )

        cached = self.valuation_service.get_cached_current_values(
            account.account_id
        )
        if cached is None:
            raise ValueError(
                "No current valuation is available for account "
                f"{account.account_number}. Run Update Portfolio first."
            )

        holdings, cash, _total_value, _daily_change = cached
        valuation_date = snapshot.snapshot_date if snapshot else date.today()
        updated_at = snapshot.valuation_updated_at if snapshot else None

        rows: list[dict[str, str]] = []
        for holding in holdings:
            rows.append(
                self._holding_row(
                    account,
                    holding,
                    valuation_date,
                    updated_at,
                )
            )

        for cash_item in cash:
            rows.append(
                self._cash_row(
                    account,
                    cash_item,
                    valuation_date,
                    updated_at,
                )
            )

        return rows

    @classmethod
    def _holding_row(
        cls,
        account: ExportAccount,
        holding: CurrentHolding,
        valuation_date: date,
        updated_at: datetime | None,
    ) -> dict[str, str]:
        return cls._base_row(
            account=account,
            record_type="Holding",
            valuation_date=valuation_date,
            updated_at=updated_at,
            values={
                "Symbol": holding.symbol,
                "Company Name": holding.company_name,
                "Quantity": cls._value(holding.quantity),
                "Currency": holding.currency,
                "Average Cost": cls._value(holding.average_cost),
                "Unrealized Gain": cls._value(holding.unrealized_gain),
                "Unrealized Gain %": cls._value(
                    holding.unrealized_gain_percent
                ),
                "Previous Close": cls._value(holding.previous_close),
                "Current Price": cls._value(holding.current_price),
                "Daily Change": cls._value(holding.daily_change),
                "Daily Change %": cls._value(holding.daily_change_percent),
                "Current Value (CAD)": cls._value(
                    holding.current_market_value
                ),
                "Is Current": str(bool(holding.is_current)),
            },
        )

    @classmethod
    def _cash_row(
        cls,
        account: ExportAccount,
        cash: CurrentCash,
        valuation_date: date,
        updated_at: datetime | None,
    ) -> dict[str, str]:
        return cls._base_row(
            account=account,
            record_type="Cash",
            valuation_date=valuation_date,
            updated_at=updated_at,
            values={
                "Currency": cash.currency,
                "Current Value (CAD)": cls._value(cash.current_cad_value),
                "Cash Amount": cls._value(cash.amount),
                "Is Current": "True",
            },
        )

    @classmethod
    def _base_row(
        cls,
        account: ExportAccount,
        record_type: str,
        valuation_date: date,
        updated_at: datetime | None,
        values: dict[str, str],
    ) -> dict[str, str]:
        row = {header: "" for header in cls.HEADERS}
        row.update(
            {
                "Record Type": record_type,
                "Brokerage": account.brokerage,
                "Account Number": account.account_number,
                "Account Name": account.name,
                "Account Type": account.account_type,
                "Valuation Date": valuation_date.isoformat(),
                "Valuation Updated At": (
                    updated_at.isoformat(sep=" ", timespec="seconds")
                    if updated_at is not None
                    else ""
                ),
            }
        )
        row.update(values)
        return row

    @staticmethod
    def _value(value) -> str:
        return "" if value is None else str(value)

    @staticmethod
    def _account_filename(account: ExportAccount) -> str:
        brokerage = AccountExportService._safe_filename(account.brokerage)
        number = AccountExportService._safe_filename(account.account_number)
        return f"{brokerage}_{number}.csv"

    @staticmethod
    def _safe_filename(value: str) -> str:
        value = re.sub(r"[<>:\"/\\|?*]", "_", value.strip())
        value = re.sub(r"\s+", "_", value)
        return value or "Account"

    @classmethod
    def _write_csv(
        cls,
        path: Path,
        rows: Iterable[dict[str, str]],
    ) -> None:
        with path.open(
            "w",
            newline="",
            encoding="utf-8-sig",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=cls.HEADERS,
                extrasaction="ignore",
            )
            writer.writeheader()
            writer.writerows(rows)
