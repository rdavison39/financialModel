"""
Unit tests for import_service.py.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from src.database.unit_of_work import UnitOfWork
from src.dto.imported_account import ImportedAccount
from src.dto.imported_cash import ImportedCash
from src.dto.imported_position import ImportedPosition
from src.services.import_service import ImportService


def test_import_data_persists_imported_account(
    session: Session,
) -> None:
    """
    ImportService persists imported DTOs into database records.
    """

    service = ImportService(UnitOfWork(session))

    account = _imported_account()

    result = service.import_data(
        [account],
        Path("data/raw/bmo.xlsx"),
    )

    uow = UnitOfWork(session)

    assert result.success is True
    assert result.import_id is not None
    assert result.accounts_imported == 1
    assert result.positions_imported == 2
    assert result.cash_balances_imported == 1
    assert result.brokerages_created == 1
    assert result.accounts_created == 1
    assert result.companies_created == 2

    assert uow.brokerages.count() == 1
    assert uow.accounts.count() == 1
    assert uow.companies.count() == 2
    assert uow.imports.count() == 1
    assert uow.holdings.count() == 2
    assert uow.cash_balances.count() == 1

    holdings = uow.holdings.find_by_import(result.import_id)

    assert holdings[0].shares == Decimal("10.000000")
    assert holdings[0].average_cost == Decimal("20.000000")
    assert holdings[0].imported_unrealized_gain == Decimal("50.00")


def test_import_data_reuses_existing_master_records(
    session: Session,
) -> None:
    """
    Repeated imports create new snapshots but reuse master data.
    """

    service = ImportService(UnitOfWork(session))
    account = _imported_account()

    first_result = service.import_data(
        [account],
        Path("data/raw/bmo-first.xlsx"),
    )

    second_result = service.import_data(
        [account],
        Path("data/raw/bmo-second.xlsx"),
    )

    uow = UnitOfWork(session)

    assert first_result.success is True
    assert second_result.success is True
    assert second_result.brokerages_created == 0
    assert second_result.accounts_created == 0
    assert second_result.companies_created == 0

    assert uow.brokerages.count() == 1
    assert uow.accounts.count() == 1
    assert uow.companies.count() == 2
    assert uow.imports.count() == 2
    assert uow.holdings.count() == 4
    assert uow.cash_balances.count() == 2


def test_import_data_rejects_empty_account_list(
    session: Session,
) -> None:
    """
    ImportService requires at least one account.
    """

    service = ImportService(UnitOfWork(session))

    with pytest.raises(ValueError):
        service.import_data(
            [],
            Path("data/raw/bmo.xlsx"),
        )

    uow = UnitOfWork(session)

    assert uow.imports.count() == 0
    assert uow.holdings.count() == 0
    assert uow.cash_balances.count() == 0


def test_import_data_rejects_duplicate_cash_currency(
    session: Session,
) -> None:
    """
    One account cannot import two cash balances for one currency.
    """

    service = ImportService(UnitOfWork(session))
    account = _imported_account()
    account.add_cash(
        ImportedCash(
            currency="CAD",
            amount=Decimal("25.00"),
        )
    )

    with pytest.raises(ValueError):
        service.import_data(
            [account],
            Path("data/raw/bmo.xlsx"),
        )

    uow = UnitOfWork(session)

    assert uow.imports.count() == 0
    assert uow.holdings.count() == 0
    assert uow.cash_balances.count() == 0


def _imported_account() -> ImportedAccount:
    """
    Create a representative imported account DTO.
    """

    account = ImportedAccount(
        account_number="22427503",
        account_name="BMO TFSA",
        account_type="TFSA",
        statement_date=date(2026, 6, 28),
    )

    account.add_cash(
        ImportedCash(
            currency="CAD",
            amount=Decimal("123.45"),
        )
    )

    account.add_position(
        ImportedPosition(
            symbol="BNS",
            description="Bank of Nova Scotia",
            security_type="Equity",
            currency="CAD",
            quantity=Decimal("10"),
            unit_price=Decimal("25"),
            market_value=Decimal("250"),
            cost_basis=Decimal("200"),
        )
    )

    account.add_position(
        ImportedPosition(
            symbol="TD",
            description="Toronto-Dominion Bank",
            security_type="Equity",
            currency="CAD",
            quantity=Decimal("5"),
            unit_price=Decimal("80"),
            market_value=Decimal("400"),
            cost_basis=Decimal("375"),
        )
    )

    return account
