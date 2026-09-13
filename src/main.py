"""
Command-line entry point for importing BMO InvestorLine workbooks.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from src.database.database import database
from src.services.bmo_workbook_import_runner import import_bmo_workbook
from src.services.import_result_formatter import format_import_result
from src.utils.logger import logger

SUPPORTED_WORKBOOK_SUFFIXES = frozenset({".xlsx", ".xlsm"})


def workbook_path(value: str) -> Path:
    """
    Validate and return a BMO workbook path supplied at the command line.
    """

    path = Path(value)

    if not path.is_file():
        raise argparse.ArgumentTypeError(
            f"Workbook does not exist or is not a file: {path}"
        )

    if path.suffix.lower() not in SUPPORTED_WORKBOOK_SUFFIXES:
        supported = ", ".join(sorted(SUPPORTED_WORKBOOK_SUFFIXES))
        raise argparse.ArgumentTypeError(
            f"Workbook must have one of these extensions: {supported}."
        )

    return path


def parse_arguments(
    argv: Sequence[str] | None = None,
) -> argparse.Namespace:
    """
    Parse BMO import command-line arguments.
    """

    parser = argparse.ArgumentParser(
        description="Import one BMO InvestorLine workbook into SQLite."
    )
    parser.add_argument(
        "workbook",
        type=workbook_path,
        help="Path to a BMO InvestorLine .xlsx or .xlsm workbook.",
    )

    return parser.parse_args(argv)


def main(
    argv: Sequence[str] | None = None,
) -> int:
    """
    Import one BMO InvestorLine workbook and return a process exit code.
    """

    arguments = parse_arguments(argv)
    database.create_database()
    session = database.get_session()

    try:
        result = import_bmo_workbook(arguments.workbook, session)
    except Exception as error:
        logger.exception("BMO workbook import failed.")
        print(f"Import failed: {error}", file=sys.stderr)
        return 1
    finally:
        session.close()
        database.close()

    print(format_import_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
