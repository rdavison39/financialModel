from datetime import date, datetime
from decimal import Decimal

from src.models.import_record import ImportRecord
from src.services.snapshot_management_service import SnapshotManagementService


def test_import_record_cash_flow_defaults_to_zero():
    record = ImportRecord(
        brokerage_id=1,
        account_id=1,
        snapshot_date=datetime(2026, 9, 29, 12, 0),
        snapshot_day=date(2026, 9, 29),
        file_name="snapshot.xlsx",
    )
    assert record.external_added == Decimal("0")
    assert record.external_withdrawn == Decimal("0")


def test_cash_flow_amount_validation():
    assert SnapshotManagementService._amount("123.456", "$ Added") == Decimal("123.46")

    try:
        SnapshotManagementService._amount("-1", "$ Added")
    except ValueError as exc:
        assert "$ Added cannot be negative" in str(exc)
    else:
        raise AssertionError("negative amount should fail")
