from datetime import date, datetime
from decimal import Decimal

from src.services.account_export_service import AccountExportService, ExportAccount
from src.services.portfolio_valuation_service import CurrentCash, CurrentHolding


def _account() -> ExportAccount:
    return ExportAccount(
        account_id=7,
        brokerage="Bank of Montreal",
        account_number="21124537",
        name="Retirement",
        account_type="RRSP",
    )


def test_holding_row_contains_account_metadata_and_current_values():
    holding = CurrentHolding(
        symbol="RY:CA",
        company_name="Royal Bank",
        quantity=Decimal("100"),
        price=Decimal("180.25"),
        market_value=Decimal("18025.00"),
        currency="CAD",
        average_cost=Decimal("150.00"),
        unrealized_gain=Decimal("3025.00"),
        unrealized_gain_percent=Decimal("20.166666"),
        daily_change=Decimal("125.00"),
        daily_change_percent=Decimal("0.697"),
        previous_close=Decimal("179.00"),
        is_current=True,
    )

    row = AccountExportService._holding_row(
        _account(),
        holding,
        date(2026, 9, 17),
        datetime(2026, 9, 17, 15, 30, 45),
    )

    assert row["Record Type"] == "Holding"
    assert row["Brokerage"] == "Bank of Montreal"
    assert row["Account Number"] == "21124537"
    assert row["Account Type"] == "RRSP"
    assert row["Symbol"] == "RY:CA"
    assert row["Current Price"] == "180.25"
    assert row["Current Value (CAD)"] == "18025.00"
    assert row["Average Cost"] == "150.00"
    assert row["Unrealized Gain"] == "3025.00"
    assert row["Daily Change"] == "125.00"
    assert row["Previous Close"] == "179.00"
    assert row["Is Current"] == "True"
    assert row["Valuation Date"] == "2026-09-17"


def test_cash_row_contains_cash_amount_and_current_cad_value():
    cash = CurrentCash(
        currency="USD",
        amount=Decimal("1000.00"),
        current_cad_value=Decimal("1375.00"),
    )

    row = AccountExportService._cash_row(
        _account(),
        cash,
        date(2026, 9, 17),
        None,
    )

    assert row["Record Type"] == "Cash"
    assert row["Currency"] == "USD"
    assert row["Cash Amount"] == "1000.00"
    assert row["Current Value (CAD)"] == "1375.00"
    assert row["Current Price"] == ""


def test_write_csv_uses_stable_headers_and_utf8_bom(tmp_path):
    account = _account()
    row = AccountExportService._holding_row(
        account,
        CurrentHolding(
            symbol="ABC:CA",
            company_name="A Company",
            quantity=Decimal("5"),
            price=Decimal("10"),
            market_value=Decimal("50"),
            currency="CAD",
            average_cost=None,
            unrealized_gain=None,
            unrealized_gain_percent=None,
            daily_change=None,
            daily_change_percent=None,
            previous_close=Decimal("9.50"),
            is_current=True,
        ),
        date(2026, 9, 17),
        None,
    )

    path = tmp_path / "account.csv"
    AccountExportService._write_csv(path, [row])

    text = path.read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    assert lines[0].startswith("Record Type,Brokerage,Account Number")
    assert "Current Price" in lines[0]
    assert "Current Value (CAD)" in lines[0]
    assert "ABC:CA" in lines[1]
    assert "50" in lines[1]


def test_account_filename_is_safe():
    account = ExportAccount(
        account_id=1,
        brokerage="BMO / Bank of Montreal",
        account_number="12:34?56",
        name="Test",
        account_type="TFSA",
    )

    assert AccountExportService._account_filename(account) == (
        "BMO___Bank_of_Montreal_12_34_56.csv"
    )
