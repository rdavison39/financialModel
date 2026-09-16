"""
One-time repair of brokerage holding snapshot fields.

This script backfills the brokerage-supplied daily values that were added to
HoldingSnapshot after older snapshots had already been imported:

    average_cost
    unrealized_gain
    unrealized_gain_percent
    daily_change
    daily_change_percent
    previous_close

It does NOT create a new ImportRecord, change import timestamps, or alter
quantity, price, market_value, or currency.

Matching is performed against the existing ImportRecord for the same
brokerage/account/source timestamp. If an exact timestamp is not found, the
script falls back to the latest ImportRecord for that account on the same
calendar day.

Usage from the project root:

    python scripts/backfill_brokerage_snapshot_fields.py

The script is a dry run by default. To actually write the changes:

    python scripts/backfill_brokerage_snapshot_fields.py --apply

Examples with the directories used by the current project:

    python scripts/backfill_brokerage_snapshot_fields.py --apply \
        --bmo-dir "C:\\Users\\ronal\\Downloads\\bmo" \
        --nesbitt-dir "C:\\Users\\ronal\\Downloads\\nesbitt"
"""

from __future__ import annotations

import argparse
from datetime import datetime, time
from decimal import Decimal
from pathlib import Path
import sys

# When this file is executed from the scripts directory, Python does not
# automatically include the project root on sys.path. Add it explicitly so
# imports such as "from src.database import ..." work correctly.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database import get_session
from src.importers.bmo_importer import BMOImporter
from src.importers.nesbitt_importer import NesbittImporter
from src.models.account import Account
from src.models.brokerage import Brokerage
from src.models.company import Company
from src.models.holding_snapshot import HoldingSnapshot
from src.models.import_record import ImportRecord


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_BMO_DIR = Path(r"C:\Users\ronal\Downloads\bmo")
DEFAULT_NESBITT_DIR = Path(r"C:\Users\ronal\Downloads\nesbitt")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def day_bounds(snapshot_date: datetime) -> tuple[datetime, datetime]:
    """Return the inclusive/exclusive datetime range for a calendar day."""
    start = datetime.combine(snapshot_date.date(), time.min)
    end = datetime.combine(snapshot_date.date(), time.max)
    return start, end


def find_import_record(
    session: Session,
    brokerage_name: str,
    account_number: str,
    snapshot_date: datetime,
) -> ImportRecord | None:
    """
    Find the existing ImportRecord representing this source snapshot.

    Prefer an exact source timestamp. If that is not present, use the latest
    import for the same account on the same calendar day.
    """
    brokerage = session.scalar(
        select(Brokerage).where(Brokerage.name == brokerage_name)
    )

    if brokerage is None:
        return None

    account = session.scalar(
        select(Account).where(
            Account.brokerage_id == brokerage.id,
            Account.account_number == account_number,
        )
    )

    if account is None:
        return None

    exact = session.scalar(
        select(ImportRecord).where(
            ImportRecord.brokerage_id == brokerage.id,
            ImportRecord.account_id == account.id,
            ImportRecord.snapshot_date == snapshot_date,
        )
    )

    if exact is not None:
        return exact

    start, end = day_bounds(snapshot_date)

    return session.scalar(
        select(ImportRecord)
        .where(
            ImportRecord.brokerage_id == brokerage.id,
            ImportRecord.account_id == account.id,
            ImportRecord.snapshot_date >= start,
            ImportRecord.snapshot_date <= end,
        )
        .order_by(ImportRecord.snapshot_date.desc())
    )


def find_company(
    session: Session,
    symbol: str,
) -> Company | None:
    """Find a company by its unique security symbol."""
    return session.scalar(
        select(Company).where(Company.symbol == symbol)
    )


def find_holding(
    session: Session,
    account_id: int,
    snapshot_date: datetime,
    company_id: int,
) -> HoldingSnapshot | None:
    """Find a holding at an exact imported source timestamp."""
    return session.scalar(
        select(HoldingSnapshot).where(
            HoldingSnapshot.account_id == account_id,
            HoldingSnapshot.snapshot_date == snapshot_date,
            HoldingSnapshot.company_id == company_id,
        )
    )


def find_holding_same_day(
    session: Session,
    account_id: int,
    snapshot_date: datetime,
    company_id: int,
) -> HoldingSnapshot | None:
    """
    Fallback holding lookup for legacy data whose timestamp differs from the
    ImportRecord timestamp but is still on the same calendar day.
    """
    start, end = day_bounds(snapshot_date)

    return session.scalar(
        select(HoldingSnapshot)
        .where(
            HoldingSnapshot.account_id == account_id,
            HoldingSnapshot.company_id == company_id,
            HoldingSnapshot.snapshot_date >= start,
            HoldingSnapshot.snapshot_date <= end,
        )
        .order_by(HoldingSnapshot.snapshot_date.desc())
    )


def decimal(value: Decimal | None) -> Decimal:
    """Return a non-null Decimal suitable for the required DB fields."""
    return value if value is not None else Decimal("0")


# ---------------------------------------------------------------------------
# Backfill
# ---------------------------------------------------------------------------

def backfill_file(
    session: Session,
    brokerage_name: str,
    file_path: Path,
) -> tuple[int, int, int]:
    """
    Backfill one brokerage workbook.

    Returns:
        (updated, missing, skipped)
    """
    if brokerage_name == "BMO":
        imported_account = BMOImporter(file_path).import_file()
    elif brokerage_name == "Nesbitt Burns":
        imported_account = NesbittImporter(file_path).import_file()
    else:
        raise ValueError(f"Unsupported brokerage: {brokerage_name}")

    import_record = find_import_record(
        session=session,
        brokerage_name=brokerage_name,
        account_number=imported_account.account_number,
        snapshot_date=imported_account.snapshot_date,
    )

    if import_record is None:
        print(
            f"  SKIP {file_path.name}: "
            f"no existing ImportRecord for account "
            f"{imported_account.account_number} "
            f"at {imported_account.snapshot_date}"
        )
        return 0, 0, 1

    updated = 0
    missing = 0

    for imported_holding in imported_account.holdings:
        company = find_company(session, imported_holding.symbol)

        if company is None:
            print(
                f"  MISSING company {imported_holding.symbol} "
                f"in {file_path.name}"
            )
            missing += 1
            continue

        holding = find_holding(
            session=session,
            account_id=import_record.account_id,
            snapshot_date=import_record.snapshot_date,
            company_id=company.id,
        )

        if holding is None:
            holding = find_holding_same_day(
                session=session,
                account_id=import_record.account_id,
                snapshot_date=import_record.snapshot_date,
                company_id=company.id,
            )

        if holding is None:
            print(
                f"  MISSING holding {imported_holding.symbol} "
                f"for account {imported_account.account_number} "
                f"on {import_record.snapshot_date}"
            )
            missing += 1
            continue

        # These are the brokerage-authoritative fields being repaired.
        holding.average_cost = decimal(imported_holding.average_cost)
        holding.unrealized_gain = decimal(
            imported_holding.unrealized_gain
        )
        holding.unrealized_gain_percent = decimal(
            imported_holding.unrealized_gain_percent
        )
        holding.daily_change = decimal(imported_holding.daily_change)
        holding.daily_change_percent = decimal(
            imported_holding.daily_change_percent
        )
        holding.previous_close = decimal(
            imported_holding.previous_close
        )

        updated += 1

    print(
        f"  {file_path.name}: account={imported_account.account_number}, "
        f"date={imported_account.snapshot_date}, "
        f"updated={updated}, missing={missing}"
    )

    return updated, missing, 0


def iter_excel_files(directory: Path) -> list[Path]:
    """Return Excel workbooks in deterministic order."""
    if not directory.exists():
        return []

    return sorted(
        path
        for path in directory.iterdir()
        if path.is_file()
        and path.suffix.lower() in {".xlsx", ".xlsm"}
    )


def run(
    session: Session,
    bmo_dir: Path,
    nesbitt_dir: Path,
    apply_changes: bool,
) -> None:
    """Run the complete one-time backfill."""
    files = [
        ("BMO", path)
        for path in iter_excel_files(bmo_dir)
    ] + [
        ("Nesbitt Burns", path)
        for path in iter_excel_files(nesbitt_dir)
    ]

    if not files:
        raise SystemExit(
            "No Excel files found. Check --bmo-dir and --nesbitt-dir."
        )

    total_updated = 0
    total_missing = 0
    total_skipped = 0

    print()
    print("Brokerage snapshot backfill")
    print("=" * 70)
    print(f"Mode: {'APPLY' if apply_changes else 'DRY RUN'}")
    print(f"BMO directory:      {bmo_dir}")
    print(f"Nesbitt directory:  {nesbitt_dir}")
    print(f"Excel files found:  {len(files)}")
    print()

    for brokerage_name, file_path in files:
        print(f"{brokerage_name}: {file_path.name}")

        try:
            updated, missing, skipped = backfill_file(
                session=session,
                brokerage_name=brokerage_name,
                file_path=file_path,
            )

            total_updated += updated
            total_missing += missing
            total_skipped += skipped

        except Exception as exc:
            session.rollback()
            print(f"  ERROR: {exc}")

    print()
    print("-" * 70)
    print(f"Holdings updated: {total_updated}")
    print(f"Holdings missing: {total_missing}")
    print(f"Files skipped:    {total_skipped}")

    if apply_changes:
        session.commit()
        print()
        print("Changes committed to the database.")
    else:
        session.rollback()
        print()
        print("DRY RUN: no database changes were committed.")
        print("Run again with --apply to write the changes.")


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="One-time backfill of brokerage holding snapshot fields."
    )

    parser.add_argument(
        "--bmo-dir",
        type=Path,
        default=DEFAULT_BMO_DIR,
        help="Directory containing BMO Excel reports.",
    )

    parser.add_argument(
        "--nesbitt-dir",
        type=Path,
        default=DEFAULT_NESBITT_DIR,
        help="Directory containing Nesbitt Excel reports.",
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help="Commit the backfill. Without this flag the script is dry-run.",
    )

    return parser.parse_args()


def main() -> None:
    """Application entry point."""
    args = parse_args()

    with get_session() as session:
        run(
            session=session,
            bmo_dir=args.bmo_dir,
            nesbitt_dir=args.nesbitt_dir,
            apply_changes=args.apply,
        )


if __name__ == "__main__":
    main()
