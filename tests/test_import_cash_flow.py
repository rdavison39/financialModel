from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

from src.database import get_session
from src.database_init import initialize_database
from src.models.import_record import ImportRecord
from src.services.import_service import ImportService


def test_replacing_same_day_import_preserves_cash_flow():
    initialize_database()
    session = get_session()
    try:
        service = ImportService(session)
        imported = SimpleNamespace(
            account_number="TEST-CASH-FLOW",
            snapshot_date=datetime(2026, 9, 29, 10, 0),
            holdings=[],
            cash=[],
        )
        first = service.import_snapshot(
            "TEST", imported, "first.xlsx"
        )
        record = session.get(ImportRecord, first.import_record_id)
        record.external_added = Decimal("10000.00")
        record.external_withdrawn = Decimal("250.00")
        session.commit()

        imported.snapshot_date = datetime(2026, 9, 29, 15, 0)
        second = service.import_snapshot(
            "TEST", imported, "second.xlsx"
        )
        record = session.get(ImportRecord, second.import_record_id)
        assert record.external_added == Decimal("10000.00")
        assert record.external_withdrawn == Decimal("250.00")
    finally:
        session.close()
