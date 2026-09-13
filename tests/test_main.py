"""
Tests for the BMO import command-line entry point.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src import main as main_module
from src.services.import_result import ImportResult


class FakeSession:
    """
    Minimal session double used by command-line tests.
    """

    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        """
        Record that the command closed the database session.
        """

        self.closed = True


class FakeDatabase:
    """
    Minimal database service double used by command-line tests.
    """

    def __init__(self) -> None:
        self.created = False
        self.closed = False
        self.session = FakeSession()

    def create_database(self) -> None:
        """
        Record database initialization.
        """

        self.created = True

    def get_session(self) -> FakeSession:
        """
        Return the test session.
        """

        return self.session

    def close(self) -> None:
        """
        Record database shutdown.
        """

        self.closed = True


def test_workbook_path_requires_supported_existing_workbook(
    tmp_path: Path,
) -> None:
    """
    The command accepts existing Excel workbook filenames only.
    """

    workbook = tmp_path / "bmo.xlsx"
    workbook.touch()

    assert main_module.workbook_path(str(workbook)) == workbook

    unsupported_workbook = tmp_path / "bmo.csv"
    unsupported_workbook.touch()

    with pytest.raises(Exception, match="extensions"):
        main_module.workbook_path(str(unsupported_workbook))

    with pytest.raises(Exception, match="does not exist"):
        main_module.workbook_path(str(tmp_path / "missing.xlsx"))


def test_main_imports_workbook_and_prints_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    The command initializes storage, imports, and closes resources.
    """

    workbook = tmp_path / "bmo.xlsx"
    workbook.touch()
    fake_database = FakeDatabase()
    imported: list[tuple[Path, FakeSession]] = []

    def fake_import(
        path: Path,
        session: FakeSession,
    ) -> ImportResult:
        imported.append((path, session))
        return ImportResult(success=True, import_id=42)

    monkeypatch.setattr(main_module, "database", fake_database)
    monkeypatch.setattr(main_module, "import_bmo_workbook", fake_import)

    exit_code = main_module.main([str(workbook)])

    assert exit_code == 0
    assert imported == [(workbook, fake_database.session)]
    assert fake_database.created is True
    assert fake_database.session.closed is True
    assert fake_database.closed is True
    assert "Import complete." in capsys.readouterr().out


def test_main_returns_error_code_when_import_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    A failed import returns a non-zero exit code and clear error message.
    """

    workbook = tmp_path / "bmo.xlsx"
    workbook.touch()
    fake_database = FakeDatabase()

    def failed_import(
        _path: Path,
        _session: FakeSession,
    ) -> ImportResult:
        raise ValueError("Workbook is not a valid BMO export.")

    monkeypatch.setattr(main_module, "database", fake_database)
    monkeypatch.setattr(main_module, "import_bmo_workbook", failed_import)

    exit_code = main_module.main([str(workbook)])

    assert exit_code == 1
    assert fake_database.session.closed is True
    assert fake_database.closed is True
    assert "Import failed: Workbook is not a valid BMO export." in (
        capsys.readouterr().err
    )
