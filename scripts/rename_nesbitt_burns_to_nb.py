"""Rename the brokerage display name from Nesbitt Burns to NB."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow this script to be run directly from the project's scripts directory.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select

from src.database import get_session
from src.database_init import initialize_database
from src.models.brokerage import Brokerage

OLD_NAME = "Nesbitt Burns"
NEW_NAME = "NB"


def main() -> None:
    """Rename matching brokerage records."""
    parser = argparse.ArgumentParser(
        description="Rename the brokerage 'Nesbitt Burns' to 'NB'."
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Actually save the rename. Without this flag, only report matches.",
    )
    args = parser.parse_args()

    initialize_database()
    session = get_session()

    try:
        rows = session.scalars(
            select(Brokerage).where(Brokerage.name == OLD_NAME)
        ).all()

        print(f"Found {len(rows)} brokerage record(s) named '{OLD_NAME}'.")

        if not rows:
            return

        if not args.yes:
            print("DRY RUN — nothing was changed.")
            print("Run with --yes to rename them to 'NB'.")
            return

        for brokerage in rows:
            brokerage.name = NEW_NAME

        session.commit()
        print(f"Renamed {len(rows)} brokerage record(s) to '{NEW_NAME}'.")

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
