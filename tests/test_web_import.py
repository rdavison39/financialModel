"""Tests for the Sprint 4.7 web import page."""

from datetime import datetime
from io import BytesIO
from types import SimpleNamespace

from fastapi.testclient import TestClient

from src.api.main import app, get_db


class DummySession:
    """Session stand-in for web-route tests."""

    def __init__(self) -> None:
        self.rolled_back = False

    def rollback(self) -> None:
        self.rolled_back = True


class DummyUpload:
    """Minimal upload object for direct web-route tests."""

    def __init__(self, filename: str, content: bytes) -> None:
        self.filename = filename
        self.file = BytesIO(content)


def setup_function():
    app.dependency_overrides[get_db] = lambda: DummySession()


def teardown_function():
    app.dependency_overrides.clear()


def test_import_page_renders():
    response = TestClient(app).get("/import")
    assert response.status_code == 200
    assert "Upload a brokerage Excel snapshot" in response.text
    assert 'name="brokerage"' in response.text
    assert 'name="upload"' in response.text


def test_import_rejects_unsupported_extension():
    response = TestClient(app).post(
        "/import",
        data={"brokerage": "BMO"},
        files={"upload": ("statement.pdf", b"not excel", "application/pdf")},
    )
    assert response.status_code == 400
    assert "Only .xlsx and .xlsm Excel files are supported" in response.text


def test_import_uses_existing_importer_and_service(monkeypatch):
    calls = {}

    class FakeImporter:
        def __init__(self, path):
            calls["path"] = path

        def import_file(self):
            calls["imported"] = True
            return SimpleNamespace(
                account_number="123456",
                snapshot_date=datetime(2026, 9, 24, 12, 0),
                holdings=[],
                cash=[],
            )

    class FakeImportService:
        def __init__(self, session):
            calls["session"] = session

        def import_snapshot(self, **kwargs):
            calls["kwargs"] = kwargs
            return SimpleNamespace(
                account_number="123456",
                snapshot_date=datetime(2026, 9, 24, 12, 0),
                holdings_imported=7,
                cash_imported=2,
                duplicate=False,
            )

    monkeypatch.setattr("src.api.main.BMOImporter", FakeImporter)
    monkeypatch.setattr("src.api.main.ImportService", FakeImportService)

    response = TestClient(app).post(
        "/import",
        data={"brokerage": "BMO"},
        files={
            "upload": (
                "Bmo-1.xlsx",
                b"fake workbook",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 200
    assert "Import complete" in response.text
    assert "123456" in response.text
    assert "7" in response.text
    assert calls["imported"] is True
    assert calls["kwargs"]["brokerage_name"] == "BMO"
    assert calls["kwargs"]["file_name"] == "Bmo-1.xlsx"


def test_import_failure_rolls_back(monkeypatch):
    session = DummySession()
    app.dependency_overrides[get_db] = lambda: session

    class FakeImporter:
        def __init__(self, path):
            pass

        def import_file(self):
            raise ValueError("bad workbook")

    monkeypatch.setattr("src.api.main.BMOImporter", FakeImporter)

    response = TestClient(app).post(
        "/import",
        data={"brokerage": "BMO"},
        files={
            "upload": (
                "Bmo-1.xlsx",
                b"bad",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 400
    assert "ValueError: bad workbook" in response.text
    assert session.rolled_back is True
