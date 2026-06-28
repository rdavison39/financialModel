"""
entity_factory.py

Factory functions for creating test entities.

These helpers create valid entities with sensible defaults. Individual
fields can be overridden by passing keyword arguments.

Objects are added to the session and flushed so primary keys are
available immediately, but the caller controls when the transaction is
committed.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from src.models.account import Account
from src.models.brokerage import Brokerage
from src.models.company import Company
from src.models.holding_snapshot import HoldingSnapshot
from src.models.import_record import Import
from src.models.market_price import MarketPrice


def create_brokerage(
    session: Session,
    **overrides,
) -> Brokerage:
    """
    Create a Brokerage.
    """

    values = {
        "name": "BMO InvestorLine",
        "importer": "BMOInvestorLineImporter",
        "website": "https://www.bmo.com/investorline",
        "active": True,
    }

    values.update(overrides)

    brokerage = Brokerage(**values)

    session.add(brokerage)
    session.flush()

    return brokerage


def create_account(
    session: Session,
    brokerage: Brokerage,
    **overrides,
) -> Account:
    """
    Create an Account.
    """

    values = {
        "brokerage_id": brokerage.id,
        "account_number": "12345678",
        "account_name": "RRSP",
        "owner": "Ron Davison",
        "account_type": "RRSP",
        "currency": "CAD",
        "active": True,
    }

    values.update(overrides)

    account = Account(**values)

    session.add(account)
    session.flush()

    return account


def create_company(
    session: Session,
    **overrides,
) -> Company:
    """
    Create a Company.
    """

    values = {
        "ticker": "BNS",
        "company_name": "Bank of Nova Scotia",
        "exchange": "TSX",
        "currency": "CAD",
        "asset_class": "Equity",
        "sector": "Financials",
        "industry": "Banks",
        "country": "Canada",
        "active": True,
    }

    values.update(overrides)

    company = Company(**values)

    session.add(company)
    session.flush()

    return company


def create_import(
    session: Session,
    brokerage: Brokerage,
    **overrides,
) -> Import:
    """
    Create an Import record.
    """

    values = {
        "brokerage_id": brokerage.id,
        "source_folder": "c:/imports",
        "file_count": 1,
        "account_count": 1,
        "holding_count": 1,
        "validation_status": "VALID",
    }

    values.update(overrides)

    record = Import(**values)

    session.add(record)
    session.flush()

    return record


def create_holding_snapshot(
    session: Session,
    import_record: Import,
    account: Account,
    company: Company,
    **overrides,
) -> HoldingSnapshot:
    """
    Create a HoldingSnapshot.
    """

    values = {
        "import_id": import_record.id,
        "account_id": account.id,
        "company_id": company.id,
        "shares": Decimal("100"),
        "average_cost": Decimal("50.00"),
        "total_cost": Decimal("5000.00"),
        "imported_price": Decimal("55.00"),
        "imported_market_value": Decimal("5500.00"),
        "imported_unrealized_gain": Decimal("500.00"),
        "imported_dividend": Decimal("2.10"),
        "imported_yield": Decimal("0.0382"),
    }

    values.update(overrides)

    holding = HoldingSnapshot(**values)

    session.add(holding)
    session.flush()

    return holding


def create_market_price(
    session: Session,
    company: Company,
    **overrides,
) -> MarketPrice:
    """
    Create a MarketPrice.
    """

    values = {
        "company_id": company.id,
        "price_date": date(2026, 6, 30),
        "open": Decimal("54.90"),
        "high": Decimal("55.30"),
        "low": Decimal("54.80"),
        "close": Decimal("55.10"),
        "volume": 1234567,
        "dividend": Decimal("0.00"),
    }

    values.update(overrides)

    price = MarketPrice(**values)

    session.add(price)
    session.flush()

    return price