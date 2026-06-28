"""
test_models.py

Unit tests for the SQLAlchemy model layer.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.models.account import Account
from src.models.brokerage import Brokerage
from src.models.company import Company
from src.models.holding_snapshot import HoldingSnapshot
from src.models.import_record import Import
from src.models.market_price import MarketPrice


def test_all_tables_exist() -> None:
    """
    Verify every ORM model defines the expected table.
    """

    assert Brokerage.__tablename__ == "brokerages"
    assert Account.__tablename__ == "accounts"
    assert Company.__tablename__ == "companies"
    assert Import.__tablename__ == "imports"
    assert HoldingSnapshot.__tablename__ == "holding_snapshots"
    assert MarketPrice.__tablename__ == "market_prices"


def test_create_brokerage() -> None:
    """
    Verify a Brokerage can be instantiated.
    """

    brokerage = Brokerage(
        name="BMO InvestorLine",
    )

    assert brokerage.name == "BMO InvestorLine"


def test_create_account() -> None:
    """
    Verify an Account can be instantiated.
    """

    account = Account(
        brokerage_id=1,
        account_number="12345678",
        account_name="RRSP",
        owner="Ron Davison",
        account_type="RRSP",
        currency="CAD",
        active=True,
    )

    assert account.account_number == "12345678"
    assert account.currency == "CAD"


def test_create_company() -> None:
    """
    Verify a Company can be instantiated.
    """

    company = Company(
        ticker="BNS",
        company_name="Bank of Nova Scotia",
        exchange="TSX",
        currency="CAD",
        asset_class="Equity",
        sector="Financials",
        industry="Banks",
        country="Canada",
        active=True,
    )

    assert company.ticker == "BNS"


def test_create_import() -> None:
    """
    Verify an Import can be instantiated.
    """

    record = Import(
        brokerage_id=1,
        source_folder="c:/imports",
        file_count=2,
        account_count=3,
        holding_count=25,
        validation_status="VALID",
    )

    assert record.file_count == 2
    assert record.validation_status == "VALID"


def test_create_holding_snapshot() -> None:
    """
    Verify a HoldingSnapshot can be instantiated.
    """

    holding = HoldingSnapshot(
        import_id=1,
        account_id=1,
        company_id=1,
        shares=Decimal("100"),
        average_cost=Decimal("50.00"),
        total_cost=Decimal("5000.00"),
        imported_price=Decimal("55.00"),
        imported_market_value=Decimal("5500.00"),
        imported_unrealized_gain=Decimal("500.00"),
        imported_dividend=Decimal("2.10"),
        imported_yield=Decimal("0.0382"),
    )

    assert holding.shares == Decimal("100")
    assert holding.company_id == 1


def test_create_market_price() -> None:
    """
    Verify a MarketPrice can be instantiated.
    """

    price = MarketPrice(
        company_id=1,
        price_date=date(2026, 6, 30),
        open=Decimal("54.90"),
        high=Decimal("55.30"),
        low=Decimal("54.80"),
        close=Decimal("55.10"),
        volume=1234567,
        dividend=Decimal("0.00"),
    )

    assert price.close == Decimal("55.10")
    assert price.volume == 1234567