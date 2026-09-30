"""
Service for importing multiple brokerage Excel snapshots.
"""

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from src.importers.bmo_importer import BMOImporter
from src.importers.nesbitt_importer import NesbittImporter
from src.services.import_service import ImportService


@dataclass
class ImportedSnapshotSummary:
    """Imported snapshot that can be edited after a bulk import."""

    import_record_id: int
    account_id: int
    account_number: str
    snapshot_date: object
    duplicate: bool
    replaced: bool


@dataclass
class BulkImportResult:
    """Summary of a directory import."""

    files_found: int
    imported: int
    replaced: int
    duplicates: int
    errors: int
    error_files: list[str]
    snapshots: list[ImportedSnapshotSummary]


class BulkImportService:
    """Imports all Excel snapshots from a brokerage directory."""

    def __init__(self, session: Session) -> None:
        """Initialize the bulk import service."""
        self.session = session
        self.import_service = ImportService(session)

    def import_bmo_directory(
        self,
        directory: str | Path,
        force_reimport: bool = False,
    ) -> BulkImportResult:
        """Import all BMO Excel files in a directory."""
        return self._import_directory(
            directory=directory,
            brokerage_name="BMO",
            importer_class=BMOImporter,
            force_reimport=force_reimport,
        )

    def import_nesbitt_directory(
        self,
        directory: str | Path,
        force_reimport: bool = False,
    ) -> BulkImportResult:
        """Import all Nesbitt Burns Excel files in a directory."""
        return self._import_directory(
            directory=directory,
            brokerage_name="Nesbitt Burns",
            importer_class=NesbittImporter,
            force_reimport=force_reimport,
        )

    def _import_directory(
        self,
        directory: str | Path,
        brokerage_name: str,
        importer_class,
        force_reimport: bool = False,
    ) -> BulkImportResult:
        """Import all Excel files from a directory."""
        directory_path = Path(directory)

        if not directory_path.exists():
            raise FileNotFoundError(
                f"Directory not found: {directory_path}"
            )

        if not directory_path.is_dir():
            raise NotADirectoryError(
                f"Path is not a directory: {directory_path}"
            )

        files = sorted(
            file
            for file in directory_path.iterdir()
            if file.is_file()
            and file.suffix.lower() in {".xlsx", ".xlsm"}
        )

        imported = 0
        replaced = 0
        duplicates = 0
        errors = 0
        error_files: list[str] = []
        snapshots: list[ImportedSnapshotSummary] = []

        for file_path in files:
            try:
                imported_account = importer_class(
                    file_path
                ).import_file()

                result = self.import_service.import_snapshot(
                    brokerage_name=brokerage_name,
                    imported_account=imported_account,
                    file_name=file_path.name,
                    force_reimport=force_reimport,
                )

                if result.duplicate:
                    duplicates += 1
                elif result.replaced:
                    replaced += 1
                else:
                    imported += 1

                if result.import_record_id is not None:
                    snapshots.append(
                        ImportedSnapshotSummary(
                            import_record_id=result.import_record_id,
                            account_id=result.account_id,
                            account_number=result.account_number,
                            snapshot_date=result.snapshot_date,
                            duplicate=result.duplicate,
                            replaced=result.replaced,
                        )
                    )

            except Exception as exc:
                self.session.rollback()
                errors += 1
                error_files.append(
                    f"{file_path.name}: {type(exc).__name__}: {exc}"
                )

        return BulkImportResult(
            files_found=len(files),
            imported=imported,
            replaced=replaced,
            duplicates=duplicates,
            errors=errors,
            error_files=error_files,
            snapshots=snapshots,
        )
