"""
Import all brokerage Excel snapshots from a directory.
"""

import sys
from pathlib import Path


# Add the project root to Python's import path.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


from src.database import get_session
from src.database_init import initialize_database
from src.services.bulk_import_service import BulkImportService


def main() -> None:
    """Import all Excel files from a brokerage directory."""

    if len(sys.argv) != 3:
        print(
            "Usage:\n"
            "  python scripts/import_directory.py BMO <directory>\n"
            "  python scripts/import_directory.py NESBITT <directory>"
        )
        sys.exit(1)

    brokerage = sys.argv[1].upper()
    directory = Path(sys.argv[2])

    initialize_database()

    session = get_session()

    try:
        service = BulkImportService(session)

        if brokerage == "BMO":
            result = service.import_bmo_directory(directory)
        elif brokerage == "NESBITT":
            result = service.import_nesbitt_directory(directory)
        else:
            print(f"Unknown brokerage: {brokerage}")
            sys.exit(1)

        print()
        print(f"Directory: {directory}")
        print(f"Files found: {result.files_found}")
        print(f"Imported: {result.imported}")
        print(f"Duplicates: {result.duplicates}")
        print(f"Errors: {result.errors}")

        if result.error_files:
            print()
            print("Files with errors:")
            for file_name in result.error_files:
                print(f"  {file_name}")

    finally:
        session.close()


if __name__ == "__main__":
    main()