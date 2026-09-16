"""
One-time repair of brokerage holding fields in existing daily snapshots.

This utility repairs the existing account/day snapshots using the brokerage
Excel reports as the source of truth.

It updates:
    - quantity
    - average_cost
    - price
    - market_value
    - unrealized_gain
    - unrealized_gain_percent
    - daily_change
    - daily_change_percent
    - previous_close
    - currency

It also replaces the CAD/USD cash rows for the same account/day.

It does NOT create ImportRecord rows and does NOT change the normal import
rules.

Usage from the project root:

    python scripts\backfill_brokerage_snapshot_fields_v2.py ^
        "C:/Users/ronal/Downloads/bmo" ^
        "C:/Users/ronal/Downloads/nesbitt"
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

# When a Python file is executed from scripts\, Python puts scripts\ on
# sys.path rather than the project root. Add the project root explicitly
# so imports from src work correctly.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select

from src.database import get_session
from src.database_init import initialize_database
from src.importers.bmo_importer import BMOImporter
from src.importers.nesbitt_importer import NesbittImporter
from src.models.account import Account
from src.models.brokerage import Brokerage
from src.models.cash_snapshot import CashSnapshot
from src.models.company import Company
from src.models.holding_snapshot import HoldingSnapshot


def find_workbooks(directory: Path) -> list[Path]:
    """Return Excel workbooks in newest-first order."""
    if not directory.exists():
        raise FileNotFoundError(
            f"Directory not found: {directory}"
        )

    return sorted(
        (
            path
            for path in directory.iterdir()
            if path.is_file()
            and path.suffix.lower() in {".xlsx", ".xlsm"}
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def get_brokerage(
    session,
    brokerage_name: str,
) -> Brokerage | None:
    """Find the brokerage by name."""
    return session.scalar(
        select(Brokerage).where(
            Brokerage.name == brokerage_name
        )
    )


def get_account(
    session,
    brokerage: Brokerage,
    account_number: str,
) -> Account | None:
    """Find an account belonging to the specified brokerage."""
    return session.scalar(
        select(Account).where(
            Account.brokerage_id == brokerage.id,
            Account.account_number == account_number,
        )
    )


def repair_account(
    session,
    brokerage_name: str,
    imported_account,
) -> tuple[int, int, bool]:
    """
    Repair one existing account/day snapshot.

    Returns:
        updated holdings, created holdings, snapshot found
    """
    brokerage = get_brokerage(
        session,
        brokerage_name,
    )

    if brokerage is None:
        return 0, 0, False

    account = get_account(
        session,
        brokerage,
        imported_account.account_number,
    )

    if account is None:
        return 0, 0, False

    snapshot_day: date = (
        imported_account.snapshot_date.date()
    )

    existing_holdings = session.scalars(
        select(HoldingSnapshot).where(
            HoldingSnapshot.account_id == account.id,
        )
    ).all()

    day_holdings = [
        holding
        for holding in existing_holdings
        if holding.snapshot_date.date() == snapshot_day
    ]

    if not day_holdings:
        return 0, 0, False

    companies = {
        company.id: company
        for company in session.scalars(select(Company)).all()
    }

    holdings_by_symbol = {}

    for holding in day_holdings:
        company = companies.get(holding.company_id)

        if company is not None:
            holdings_by_symbol[company.symbol] = holding

    updated = 0
    created = 0

    for imported_holding in imported_account.holdings:
        holding = holdings_by_symbol.get(
            imported_holding.symbol
        )

        if holding is None:
            company = session.scalar(
                select(Company).where(
                    Company.symbol == imported_holding.symbol
                )
            )

            if company is None:
                company = Company(
                    symbol=imported_holding.symbol,
                    name=imported_holding.company_name,
                )
                session.add(company)
                session.flush()

            holding = HoldingSnapshot(
                account_id=account.id,
                company_id=company.id,
                snapshot_date=imported_account.snapshot_date,
                quantity=imported_holding.quantity,
                average_cost=imported_holding.average_cost,
                price=imported_holding.price,
                market_value=imported_holding.market_value,
                unrealized_gain=(
                    imported_holding.unrealized_gain
                ),
                unrealized_gain_percent=(
                    imported_holding.unrealized_gain_percent
                ),
                daily_change=(
                    imported_holding.daily_change
                ),
                daily_change_percent=(
                    imported_holding.daily_change_percent
                ),
                previous_close=(
                    imported_holding.previous_close
                ),
                currency=imported_holding.currency,
            )

            session.add(holding)
            created += 1
            continue

        # Refresh all brokerage-authoritative values from the source file.
        holding.quantity = imported_holding.quantity
        holding.average_cost = imported_holding.average_cost
        holding.price = imported_holding.price
        holding.market_value = imported_holding.market_value
        holding.unrealized_gain = (
            imported_holding.unrealized_gain
        )
        holding.unrealized_gain_percent = (
            imported_holding.unrealized_gain_percent
        )
        holding.daily_change = (
            imported_holding.daily_change
        )
        holding.daily_change_percent = (
            imported_holding.daily_change_percent
        )
        holding.previous_close = (
            imported_holding.previous_close
        )
        holding.currency = imported_holding.currency

        updated += 1

    # Replace cash only for this account and this calendar day.
    existing_cash = session.scalars(
        select(CashSnapshot).where(
            CashSnapshot.account_id == account.id,
        )
    ).all()

    for cash in existing_cash:
        if cash.snapshot_date.date() == snapshot_day:
            session.delete(cash)

    for imported_cash in imported_account.cash:
        session.add(
            CashSnapshot(
                account_id=account.id,
                snapshot_date=(
                    imported_account.snapshot_date
                ),
                currency=imported_cash.currency,
                amount=imported_cash.amount,
            )
        )

    session.commit()

    return updated, created, True


def process_directory(
    session,
    brokerage_name: str,
    directory: Path,
    importer_class,
) -> None:
    """Repair all account/day snapshots in one brokerage directory."""
    workbooks = find_workbooks(directory)

    if not workbooks:
        print(
            f"{brokerage_name}: no Excel workbooks found."
        )
        return

    print(
        f"\n{brokerage_name}: "
        f"{len(workbooks)} workbook(s)"
    )

    # Files are processed newest first. If more than one workbook contains
    # the same account/day, use the newest workbook and ignore older copies.
    processed: set[tuple[str, date]] = set()

    for file_path in workbooks:
        imported_account = importer_class(
            file_path
        ).import_file()

        key = (
            imported_account.account_number,
            imported_account.snapshot_date.date(),
        )

        if key in processed:
            continue

        updated, created, found = repair_account(
            session=session,
            brokerage_name=brokerage_name,
            imported_account=imported_account,
        )

        processed.add(key)

        if found:
            print(
                f"  {imported_account.account_number} "
                f"{imported_account.snapshot_date:%Y-%m-%d}: "
                f"updated={updated}, "
                f"created={created} "
                f"({file_path.name})"
            )
        else:
            print(
                f"  {imported_account.account_number} "
                f"{imported_account.snapshot_date:%Y-%m-%d}: "
                f"NO EXISTING SNAPSHOT "
                f"({file_path.name})"
            )


def main() -> None:
    """Run the one-time brokerage snapshot repair."""
    if len(sys.argv) != 3:
        raise SystemExit(
            "Usage:\n"
            '  python scripts\\backfill_brokerage_snapshot_fields_v2.py '
            '"<bmo-directory>" "<nesbitt-directory>"'
        )

    bmo_directory = Path(sys.argv[1])
    nesbitt_directory = Path(sys.argv[2])

    initialize_database()

    session = get_session()

    try:
        process_directory(
            session=session,
            brokerage_name="BMO",
            directory=bmo_directory,
            importer_class=BMOImporter,
        )

        process_directory(
            session=session,
            brokerage_name="Nesbitt Burns",
            directory=nesbitt_directory,
            importer_class=NesbittImporter,
        )

        print("\nBackfill complete.")

    finally:
        session.close()


if __name__ == "__main__":
    main()
