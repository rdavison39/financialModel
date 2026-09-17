"""
Tests for the bulk import service.
"""

from pathlib import Path

from src.models.account import Account
from src.models.brokerage import Brokerage
from src.models.holding_snapshot import HoldingSnapshot
from src.services.bulk_import_service import BulkImportService


BMO_FILE = Path("data/uploads/Bmo-1.xlsx")
NESBITT_FILE = Path("data/uploads/Nesbit-1.xlsx")


def test_import_bmo_directory(session, tmp_path):
    """Import all BMO Excel files from a directory."""
    source_file = tmp_path / "Bmo-1.xlsx"
    source_file.write_bytes(BMO_FILE.read_bytes())

    service = BulkImportService(session)

    result = service.import_bmo_directory(tmp_path)

    assert result.files_found == 1
    assert result.imported == 1
    assert result.duplicates == 0
    assert result.errors == 0
    assert result.error_files == []

    brokerage = session.query(Brokerage).one()
    assert brokerage.name == "BMO"

    account = session.query(Account).one()
    assert account.account_number == "21033605"

    assert session.query(HoldingSnapshot).count() == 8


def test_import_nesbitt_directory(session, tmp_path):
    """Import all Nesbitt Excel files from a directory."""
    source_file = tmp_path / "Nesbit-1.xlsx"
    source_file.write_bytes(NESBITT_FILE.read_bytes())

    service = BulkImportService(session)

    result = service.import_nesbitt_directory(tmp_path)

    assert result.files_found == 1
    assert result.imported == 1
    assert result.duplicates == 0
    assert result.errors == 0
    assert result.error_files == []


def test_duplicate_file_is_not_imported_twice(session, tmp_path):
    """Importing the same snapshot twice should produce a duplicate."""
    source_file = tmp_path / "Bmo-1.xlsx"
    source_file.write_bytes(BMO_FILE.read_bytes())

    service = BulkImportService(session)

    first_result = service.import_bmo_directory(tmp_path)
    second_result = service.import_bmo_directory(tmp_path)

    assert first_result.imported == 1
    assert first_result.duplicates == 0

    assert second_result.imported == 0
    assert second_result.duplicates == 1
    assert second_result.errors == 0

    assert session.query(HoldingSnapshot).count() == 8


def test_multiple_files_are_imported(session, tmp_path):
    """Multiple Excel files in a directory should all be processed."""
    file_one = tmp_path / "Bmo-1.xlsx"
    file_two = tmp_path / "Bmo-2.xlsx"

    file_one.write_bytes(BMO_FILE.read_bytes())
    file_two.write_bytes(BMO_FILE.read_bytes())

    service = BulkImportService(session)

    result = service.import_bmo_directory(tmp_path)

    assert result.files_found == 2
    assert result.imported == 1
    assert result.duplicates == 1
    assert result.errors == 0

    assert session.query(HoldingSnapshot).count() == 8


def test_bad_file_does_not_stop_directory_import(session, tmp_path):
    """A bad Excel file should not prevent other files from being imported."""
    bad_file = tmp_path / "A-bad-file.xlsx"
    good_file = tmp_path / "B-good-file.xlsx"

    bad_file.write_text("This is not an Excel workbook.")
    good_file.write_bytes(BMO_FILE.read_bytes())

    service = BulkImportService(session)

    result = service.import_bmo_directory(tmp_path)

    assert result.files_found == 2
    assert result.imported == 1
    assert result.duplicates == 0
    assert result.errors == 1
    assert result.error_files == [
        "A-bad-file.xlsx: BadZipFile: File is not a zip file"
    ]

    assert session.query(HoldingSnapshot).count() == 8


def test_force_reimport_replaces_existing_snapshot(session, tmp_path):
    """Bulk import can explicitly replace an identical snapshot."""
    source_file = tmp_path / "Bmo-1.xlsx"
    source_file.write_bytes(BMO_FILE.read_bytes())

    service = BulkImportService(session)

    first_result = service.import_bmo_directory(tmp_path)
    second_result = service.import_bmo_directory(
        tmp_path,
        force_reimport=True,
    )

    assert first_result.imported == 1
    assert first_result.replaced == 0
    assert second_result.imported == 0
    assert second_result.replaced == 1
    assert second_result.duplicates == 0
    assert second_result.errors == 0
    assert session.query(HoldingSnapshot).count() == 8
