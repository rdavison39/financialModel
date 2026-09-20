from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pandas as pd

from src.services.portfolio_history_service import PortfolioHistoryService


def test_aggregated_history_returns_selected_account_values():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from src.models.base import Base
    from src.models.portfolio_snapshot import PortfolioSnapshot

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    session.add_all(
        [
            PortfolioSnapshot(
                account_id=1,
                snapshot_date=date(2026, 1, 1),
                total_value=Decimal("100"),
            ),
            PortfolioSnapshot(
                account_id=1,
                snapshot_date=date(2026, 1, 10),
                total_value=Decimal("120"),
            ),
            PortfolioSnapshot(
                account_id=2,
                snapshot_date=date(2026, 1, 1),
                total_value=Decimal("50"),
            ),
        ]
    )
    session.commit()

    service = PortfolioHistoryService(session)
    history = service.get_aggregated_history(
        date(2026, 1, 1),
        date(2026, 1, 10),
        [1, 2],
    )

    assert [(p.snapshot_date, p.total_value) for p in history] == [
        (date(2026, 1, 1), Decimal("150")),
        (date(2026, 1, 10), Decimal("170")),
    ]


@patch("yfinance.Ticker")
def test_benchmark_history_returns_daily_closes(mock_ticker):
    frame = pd.DataFrame(
        {"Close": [100.0, 102.5]},
        index=pd.to_datetime(["2026-01-02", "2026-01-05"]),
    )
    ticker = MagicMock()
    ticker.history.return_value = frame
    mock_ticker.return_value = ticker

    service = PortfolioHistoryService(MagicMock())
    result = service.get_benchmark_history(
        "^GSPC",
        date(2026, 1, 1),
        date(2026, 1, 5),
    )

    assert [(p.snapshot_date, p.value) for p in result] == [
        (date(2026, 1, 2), Decimal("100.0")),
        (date(2026, 1, 5), Decimal("102.5")),
    ]
    ticker.history.assert_called_once()


def test_benchmark_symbols_are_defined():
    assert PortfolioHistoryService.BENCHMARKS["S&P 500"] == "^GSPC"
    assert PortfolioHistoryService.BENCHMARKS["TSX Composite"] == "^GSPTSE"

