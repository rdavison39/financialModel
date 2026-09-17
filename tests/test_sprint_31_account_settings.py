"""
Tests for Sprint 3.1 account classification and portfolio inclusion settings.
"""

from src.models.account import Account
from src.models.brokerage import Brokerage
from src.services.account_service import AccountService


def _create_account(session):
    brokerage = Brokerage(name="Test Brokerage")
    session.add(brokerage)
    session.flush()

    account = Account(
        brokerage_id=brokerage.id,
        account_number="12345",
        name="Test Account",
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


def test_new_account_defaults_to_included(session):
    account = _create_account(session)

    assert account.include_in_portfolio is True
    assert account.account_type is None


def test_update_account_settings_persists_type_and_inclusion(session):
    account = _create_account(session)

    AccountService(session).update_settings(
        account.id,
        "RRSP",
        False,
    )

    refreshed = session.get(Account, account.id)
    assert refreshed is not None
    assert refreshed.account_type == "RRSP"
    assert refreshed.include_in_portfolio is False


def test_update_account_settings_accepts_all_supported_types(session):
    account = _create_account(session)
    service = AccountService(session)

    for account_type in service.ACCOUNT_TYPES:
        service.update_settings(account.id, account_type, True)
        refreshed = session.get(Account, account.id)
        assert refreshed.account_type == account_type


def test_update_account_settings_allows_unclassified_account(session):
    account = _create_account(session)

    AccountService(session).update_settings(
        account.id,
        None,
        True,
    )

    refreshed = session.get(Account, account.id)
    assert refreshed is not None
    assert refreshed.account_type is None
    assert refreshed.include_in_portfolio is True


def test_update_account_settings_rejects_invalid_type(session):
    account = _create_account(session)

    try:
        AccountService(session).update_settings(
            account.id,
            "RESP2",
            True,
        )
    except ValueError as exc:
        assert "Invalid account type" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid account type")


def test_account_summary_contains_settings(session):
    account = _create_account(session)
    AccountService(session).update_settings(account.id, "TFSA", False)

    summary = AccountService(session).get_summaries()[0]

    assert summary.account_type == "TFSA"
    assert summary.include_in_portfolio is False
