"""Tests for background portfolio updates."""

from decimal import Decimal
import queue

import src.gui.portfolio_tab as portfolio_tab_module


def test_update_worker_queues_completion_and_closes_session(monkeypatch):
    """The valuation work runs without touching Tkinter widgets."""

    tab = portfolio_tab_module.PortfolioTab.__new__(
        portfolio_tab_module.PortfolioTab
    )
    tab._update_queue = queue.Queue()

    class FakeSession:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    session = FakeSession()
    state = {}

    def fake_initialize_database():
        state["initialized"] = True

    def fake_get_session():
        return session

    class FakeService:
        def __init__(self, supplied_session, progress_callback):
            assert supplied_session is session
            progress_callback(2, 4, "TEST")

        def update_all_accounts(self):
            return Decimal("123.45")

        tsx_daily_change_percent = Decimal("1.25")

    monkeypatch.setattr(
        portfolio_tab_module,
        "initialize_database",
        fake_initialize_database,
    )
    monkeypatch.setattr(
        portfolio_tab_module,
        "get_session",
        fake_get_session,
    )
    monkeypatch.setattr(
        portfolio_tab_module,
        "PortfolioValuationService",
        FakeService,
    )

    tab._run_portfolio_update_worker()

    assert state["initialized"] is True
    assert tab._update_queue.get_nowait() == (
        "progress",
        2,
        4,
        "TEST",
    )
    assert tab._update_queue.get_nowait() == (
        "complete",
        Decimal("123.45"),
        Decimal("1.25"),
    )
    assert session.closed is True


def test_update_worker_queues_error_and_closes_session(monkeypatch):
    """Worker failures are returned to the GUI thread as simple values."""

    tab = portfolio_tab_module.PortfolioTab.__new__(
        portfolio_tab_module.PortfolioTab
    )
    tab._update_queue = queue.Queue()

    class FakeSession:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    session = FakeSession()

    def fake_initialize_database():
        pass

    def fake_get_session():
        return session

    class FailingService:
        def __init__(self, supplied_session, progress_callback):
            assert supplied_session is session

        def update_all_accounts(self):
            raise RuntimeError("test failure")

    monkeypatch.setattr(
        portfolio_tab_module,
        "initialize_database",
        fake_initialize_database,
    )
    monkeypatch.setattr(
        portfolio_tab_module,
        "get_session",
        fake_get_session,
    )
    monkeypatch.setattr(
        portfolio_tab_module,
        "PortfolioValuationService",
        FailingService,
    )

    tab._run_portfolio_update_worker()

    assert tab._update_queue.get_nowait() == (
        "error",
        "RuntimeError",
        "test failure",
    )
    assert session.closed is True
