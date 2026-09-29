from types import SimpleNamespace

from fastapi.testclient import TestClient

from src.api import main


class FakeSession:
    def close(self):
        pass


def test_accounts_page_uses_account_service(monkeypatch):
    summaries = [
        SimpleNamespace(
            account_id=7,
            brokerage_name="BMO",
            account_number="123456",
            name="Primary",
            account_type="RRSP",
            include_in_portfolio=True,
            current_value=12345.67,
            cash_by_currency={"CAD": 1000},
            holdings_count=4,
            last_import="2026-09-24 12:00",
        )
    ]

    class FakeAccountService:
        def __init__(self, session):
            self.session = session

        def get_summaries(self):
            return summaries

    captured = {}

    def fake_template_response(**kwargs):
        captured.update(kwargs)
        return kwargs

    monkeypatch.setattr(main, "AccountService", FakeAccountService)
    monkeypatch.setattr(main.templates, "TemplateResponse", fake_template_response)

    response = main.web_accounts("request", FakeSession())

    assert response["name"] == "accounts.html"
    assert response["context"]["accounts"] == summaries


def test_rename_account_calls_account_service(monkeypatch):
    calls = []

    class FakeAccountService:
        def __init__(self, session):
            pass

        def rename(self, account_id, name):
            calls.append((account_id, name))

    monkeypatch.setattr(main, "AccountService", FakeAccountService)

    response = main.web_rename_account(7, FakeSession(), " New Name ")

    assert calls == [(7, " New Name ")]
    assert response.status_code == 303
    assert response.headers["location"] == "/accounts"


def test_account_settings_calls_account_service(monkeypatch):
    calls = []

    class FakeAccountService:
        def __init__(self, session):
            pass

        def update_settings(self, **kwargs):
            calls.append(kwargs)

    monkeypatch.setattr(main, "AccountService", FakeAccountService)

    response = main.web_account_settings(7, FakeSession(), " TFSA ", True)

    assert calls == [
        {
            "account_id": 7,
            "account_type": "TFSA",
            "include_in_portfolio": True,
        }
    ]
    assert response.status_code == 303
    assert response.headers["location"] == "/accounts"
