"""FastAPI application entry point for the Financial Model."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
import threading
import tempfile
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.schemas import (
    AccountHistoryPointResponse,
    AccountSummaryResponse,
    PortfolioCashResponse,
    PortfolioHistoryPointResponse,
    PortfolioHoldingResponse,
    PortfolioResponse,
)
from src.database import get_session
from src.database_init import initialize_database
from src.models.account import Account
from src.models.portfolio_snapshot import PortfolioSnapshot
from src.models.brokerage import Brokerage
from src.importers.bmo_importer import BMOImporter
from src.importers.nesbitt_importer import NesbittImporter
from src.services.account_comparison_history_service import (
    AccountComparisonHistoryService,
)
from src.services.account_service import AccountService
from src.services.import_service import ImportService
from src.services.portfolio_comparison_service import PortfolioComparisonService
from src.services.portfolio_history_service import PortfolioHistoryService
from src.services.portfolio_service import PortfolioService
from src.services.snapshot_management_service import SnapshotManagementService


# Portfolio web update progress is kept in-process because the web application
# runs as a single application process on the local/Raspberry Pi deployment.
_portfolio_update_lock = threading.Lock()
_portfolio_update_state = {
    "running": False,
    "count": 0,
    "total": 0,
    "symbol": "",
    "percent": 0,
    "message": "",
    "error": False,
}


def _set_portfolio_update_state(**values) -> None:
    """Update the thread-safe web portfolio progress state."""
    with _portfolio_update_lock:
        _portfolio_update_state.update(values)


def _get_portfolio_update_state() -> dict:
    """Return a snapshot of the current web portfolio progress state."""
    with _portfolio_update_lock:
        return dict(_portfolio_update_state)


def _run_portfolio_update_background() -> None:
    """Run portfolio valuation in the background and publish progress."""
    session = None

    def progress_callback(count: int, total: int, symbol: str) -> None:
        percent = 0 if total <= 0 else min(100, int(count * 100 / total))
        _set_portfolio_update_state(
            count=count,
            total=total,
            symbol=symbol,
            percent=percent,
            message=f"Updating Portfolio: {percent}% — {count} / {total} — {symbol}",
            error=False,
        )

    try:
        initialize_database()
        session = get_session()
        from src.services.portfolio_valuation_service import PortfolioValuationService

        service = PortfolioValuationService(
            session,
            progress_callback=progress_callback,
        )
        total_value = service.update_all_accounts()
        _set_portfolio_update_state(
            running=False,
            count=_get_portfolio_update_state()["total"],
            percent=100,
            symbol="",
            message=f"Portfolio updated: ${total_value:,.2f}",
            error=False,
        )
    except Exception as exc:
        _set_portfolio_update_state(
            running=False,
            message=f"Portfolio update failed: {type(exc).__name__}: {exc}",
            error=True,
        )
    finally:
        if session is not None:
            session.close()


app = FastAPI(
    title="Davison Financial Model API",
    version="0.3.0",
)

SRC_DIR = Path(__file__).resolve().parent.parent
app.mount("/static", StaticFiles(directory=SRC_DIR / "static"), name="static")
templates = Jinja2Templates(directory=SRC_DIR / "templates")

NAVIGATION = [
    {"label": "Portfolio", "path": "/portfolio"},
    {"label": "Portfolio History", "path": "/portfolio/history"},
    {"label": "Manage Snapshots", "path": "/snapshots"},
    {"label": "Account Management", "path": "/accounts"},
    {"label": "Account History", "path": "/accounts/history"},
    {"label": "Holdings History", "path": "/holdings/history"},
    {"label": "Import", "path": "/import"},
]

WEB_PAGES = {
    "/portfolio": {
        "title": "Portfolio",
        "description": "Current portfolio overview.",
        "message": "",
        "icon": "▣",
    },
    "/accounts": {
        "title": "Account Management",
        "description": "Investment accounts and portfolio inclusion settings.",
        "message": "The page shell is ready for the existing AccountService functionality.",
        "icon": "▤",
    },
    "/import": {
        "title": "Import",
        "description": "Import brokerage files into the financial model.",
        "message": "The page shell is ready for the existing import workflow.",
        "icon": "⇧",
    },
}

HISTORY_VIEWS = (
    "Portfolio Value",
    "% Growth Since Start",
    "Day's Gain/Loss",
    "% Day's Gain/Loss",
)
BENCHMARKS = ("None", "S&P 500", "TSX Composite", "Custom")
DEFAULT_BENCHMARK = "TSX Composite"


def get_db() -> Session:
    """Provide a database session for one API request."""
    session = get_session()
    try:
        yield session
    finally:
        session.close()


def _decimal(value: Decimal | None) -> str | None:
    """Serialize financial Decimal values without converting to float."""
    return None if value is None else str(value)


def _date(value: date | None) -> str | None:
    """Serialize dates/datetimes using ISO-8601 text."""
    return None if value is None else value.isoformat()


def _date_range(
    start_date: date | None,
    end_date: date | None,
) -> tuple[date, date]:
    """Resolve the API's default one-year date range."""
    end = end_date or date.today()
    start = start_date or (end - timedelta(days=365))
    if start > end:
        raise HTTPException(
            status_code=400,
            detail="start_date must be on or before end_date.",
        )
    return start, end


def _stable_account_key(
    brokerage_name: str,
    account_number: str,
    account_name: str,
) -> str:
    """Return the stable account-selection key used by the desktop UI."""
    return f"{brokerage_name}|{account_number}|{account_name}"


def _history_accounts(session: Session) -> list[dict[str, object]]:
    """Return account choices using the desktop stable selection key."""
    accounts = AccountComparisonHistoryService(session).get_accounts()
    return [
        {
            "id": item.account_id,
            "key": _stable_account_key(
                item.brokerage_name,
                item.account_number,
                item.account_name,
            ),
            "label": item.label,
        }
        for item in accounts
    ]


def _selected_account_ids(
    accounts: list[dict[str, object]],
    selected_keys: list[str] | None,
) -> list[int]:
    """Resolve stable account-selection keys to database IDs."""
    if not selected_keys:
        return [int(item["id"]) for item in accounts]

    selected = set(selected_keys)
    return [
        int(item["id"])
        for item in accounts
        if str(item["key"]) in selected
    ]


def _is_percent_view(view: str) -> bool:
    """Return whether a history view is percentage-based."""
    return view in {"% Growth Since Start", "% Day's Gain/Loss"}


def _benchmark_symbol(name: str, custom_symbol: str) -> str | None:
    """Resolve a benchmark name to a Yahoo Finance symbol."""
    if name == "None":
        return None
    if name == "Custom":
        return custom_symbol.strip() or None
    return PortfolioHistoryService.BENCHMARKS.get(name)


def _trading_dates(
    service: PortfolioHistoryService,
    start_date: date,
    end_date: date,
) -> set[date]:
    """Return actual TSX trading dates for performance views."""
    try:
        points = service.get_benchmark_history(
            PortfolioHistoryService.BENCHMARKS["TSX Composite"],
            start_date,
            end_date,
        )
    except Exception:
        return set()
    return {point.snapshot_date for point in points}


def _benchmark_series(
    service: PortfolioHistoryService,
    benchmark_name: str,
    custom_symbol: str,
    view: str,
    history,
    plot_dates: set[date] | None = None,
) -> list[dict[str, object]]:
    """Build the selected benchmark series using shared service calculations."""
    symbol = _benchmark_symbol(benchmark_name, custom_symbol)
    if not symbol or not _is_percent_view(view) or not history:
        return []

    effective_range = service.calculate_effective_date_range(
        history[0].snapshot_date,
        history[-1].snapshot_date,
        history,
    )
    if effective_range is None:
        return []

    effective_start, effective_end = effective_range
    daily_change_view = view == "% Day's Gain/Loss"
    query_start = service.calculate_benchmark_query_start(
        effective_start,
        daily_change_view=daily_change_view,
    )

    try:
        raw = service.get_benchmark_history(symbol, query_start, effective_end)
    except Exception:
        return []

    benchmark_points, previous_close = service.filter_benchmark_history(
        raw,
        effective_start,
        effective_end,
    )
    if not benchmark_points:
        return []

    if view == "% Growth Since Start":
        values = service.calculate_benchmark_growth(benchmark_points)
    else:
        values = service.calculate_benchmark_daily_change_percent_values(
            benchmark_points,
            previous_close=previous_close,
        )

    value_by_date = {
        point.snapshot_date: value
        for point, value in zip(benchmark_points, values)
    }
    dates = (plot_dates & value_by_date.keys()) if plot_dates is not None else value_by_date.keys()
    return [
        {"date": point.isoformat(), "value": str(value_by_date[point])}
        for point in sorted(dates)
    ]


def _portfolio_history_series(
    points,
    view: str,
    trading_dates: set[date],
) -> list[dict[str, object]]:
    """Transform portfolio history using the shared service calculation API."""
    selected = (
        points
        if view == "Portfolio Value"
        else [point for point in points if point.snapshot_date in trading_dates]
    )
    values = PortfolioHistoryService.calculate_metric_values(selected, view)
    return [
        {
            "date": point.snapshot_date.isoformat(),
            "value": None if value is None else str(value),
        }
        for point, value in zip(selected, values)
    ]


def _account_history_series(
    history: dict[int, list],
    account_labels: dict[int, str],
    view: str,
    trading_dates: set[date],
) -> list[dict[str, object]]:
    """Transform selected account histories using shared service calculations."""
    result = []
    for account_id, points in history.items():
        selected = (
            points
            if view == "Portfolio Value"
            else [point for point in points if point.snapshot_date in trading_dates]
        )
        values = PortfolioHistoryService.calculate_metric_values(selected, view)
        result.append(
            {
                "label": account_labels[account_id],
                "points": [
                    {
                        "date": point.snapshot_date.isoformat(),
                        "value": str(value),
                    }
                    for point, value in zip(selected, values)
                    if value is not None
                ],
            }
        )
    return result


def _brokerage_history_series(
    service: PortfolioHistoryService,
    points,
    view: str,
    trading_dates: set[date],
    brokerage_ids: dict[str, list[int]],
    selected_brokerages: list[str],
) -> list[dict[str, object]]:
    """Build optional combined brokerage series using shared calculations."""
    if view not in {"% Growth Since Start", "% Day's Gain/Loss"}:
        return []

    result = []
    for brokerage_name in selected_brokerages:
        account_ids = brokerage_ids.get(brokerage_name, [])
        if not account_ids or not points:
            continue

        brokerage_points = service.get_aggregated_history(
            points[0].snapshot_date,
            points[-1].snapshot_date,
            account_ids,
        )
        selected = [
            point for point in brokerage_points
            if point.snapshot_date in trading_dates
        ]
        values = service.calculate_metric_values(selected, view)

        result.append(
            {
                "label": brokerage_name,
                "points": [
                    {
                        "date": point.snapshot_date.isoformat(),
                        "value": str(value),
                    }
                    for point, value in zip(selected, values)
                    if value is not None
                ],
                "brokerage": True,
            }
        )

    return result


def _render_history_page(
    request: Request,
    session: Session,
    *,
    page_type: str,
    start_date: date | None,
    end_date: date | None,
    selected_keys: list[str] | None,
    view: str,
    benchmark: str,
    custom_benchmark: str,
    brokerage_lines: list[str] | None = None,
):
    """Build and render the common portfolio/account history page."""
    start, end = _date_range(start_date, end_date)
    if view not in HISTORY_VIEWS:
        view = "Portfolio Value"
    if benchmark not in BENCHMARKS:
        benchmark = DEFAULT_BENCHMARK
    if not _is_percent_view(view):
        benchmark = "None"

    selected_brokerages = [name for name in (brokerage_lines or []) if name in {"BMO", "NB"}]

    accounts = _history_accounts(session)
    account_ids = _selected_account_ids(accounts, selected_keys)
    selected_key_set = (
        set(selected_keys)
        if selected_keys
        else {str(item["key"]) for item in accounts}
    )

    history_service = PortfolioHistoryService(session)
    trading_dates = _trading_dates(history_service, start, end) if _is_percent_view(view) else set()

    chart_series: list[dict[str, object]] = []
    table_rows: list[dict[str, object]] = []

    if page_type == "portfolio":
        points = history_service.get_aggregated_history(start, end, account_ids)
        series = _portfolio_history_series(points, view, trading_dates)
        chart_series = [{"label": "Portfolio", "points": series}]
        selected_points = (
            points
            if view == "Portfolio Value"
            else [point for point in points if point.snapshot_date in trading_dates]
        )
        metric_values = history_service.calculate_metric_values(
            selected_points,
            view,
        )
        table_rows = [
            {"date": point.snapshot_date, "value": value}
            for point, value in zip(selected_points, metric_values)
            if value is not None
        ]
    else:
        histories = AccountComparisonHistoryService(session).get_histories(
            account_ids,
            start,
            end,
        )
        labels = {
            int(item["id"]): str(item["label"])
            for item in accounts
            if int(item["id"]) in account_ids
        }
        chart_series = _account_history_series(
            histories,
            labels,
            view,
            trading_dates,
        )
        for account_id, points in histories.items():
            selected_points = (
                points
                if view == "Portfolio Value"
                else [point for point in points if point.snapshot_date in trading_dates]
            )
            metric_values = history_service.calculate_metric_values(
                selected_points,
                view,
            )
            for point, value in zip(selected_points, metric_values):
                if value is not None:
                    table_rows.append(
                        {
                            "date": point.snapshot_date,
                            "label": labels.get(account_id, str(account_id)),
                            "value": value,
                        }
                    )

    if page_type == "portfolio" and _is_percent_view(view) and selected_brokerages:
        brokerage_ids: dict[str, list[int]] = {"BMO": [], "NB": []}
        for item in accounts:
            if int(item["id"]) in account_ids:
                key = str(item["key"])
                brokerage_name = key.split("|", 1)[0]
                if brokerage_name in brokerage_ids:
                    brokerage_ids[brokerage_name].append(int(item["id"]))

        chart_series.extend(
            _brokerage_history_series(
                history_service,
                points,
                view,
                trading_dates,
                brokerage_ids,
                selected_brokerages,
            )
        )

    benchmark_history_points = []
    plot_dates = None
    if page_type == "portfolio":
        benchmark_history_points = (
            points
            if view == "Portfolio Value"
            else [point for point in points if point.snapshot_date in trading_dates]
        )
        plot_dates = {point.snapshot_date for point in benchmark_history_points}
    elif histories:
        benchmark_history_points = [
            point
            for account_points in histories.values()
            for point in account_points
            if view == "Portfolio Value" or point.snapshot_date in trading_dates
        ]

    benchmark_series = _benchmark_series(
        history_service,
        benchmark,
        custom_benchmark,
        view,
        benchmark_history_points,
        plot_dates=plot_dates,
    )
    if benchmark_series:
        chart_series.append({"label": benchmark, "points": benchmark_series, "benchmark": True})

    return templates.TemplateResponse(
        request=request,
        name="history.html",
        context={
            "title": "Portfolio History" if page_type == "portfolio" else "Account History",
            "description": (
                "Historical portfolio value and performance."
                if page_type == "portfolio"
                else "Historical performance for selected accounts."
            ),
            "navigation": NAVIGATION,
            "view": view,
            "views": HISTORY_VIEWS,
            "benchmark": benchmark,
            "benchmarks": BENCHMARKS,
            "custom_benchmark": custom_benchmark,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "accounts": accounts,
            "selected_keys": selected_key_set,
            "chart_series": chart_series,
            "table_rows": sorted(
                table_rows,
                key=lambda row: (row.get("date"), row.get("label", "")),
            ),
            "percent_view": _is_percent_view(view),
            "brokerage_lines": selected_brokerages,
            "brokerage_line_options": ["BMO", "NB"],
        },
    )


def _portfolio_page_context(session: Session) -> dict:
    """Build the saved current portfolio values used by the desktop Portfolio page."""
    summaries = AccountService(session).get_summaries()
    included = [item for item in summaries if item.include_in_portfolio]

    total_value = sum(
        (item.current_value or Decimal("0") for item in included),
        Decimal("0"),
    )

    account_ids = [item.account_id for item in included]
    daily_rows = []
    if account_ids:
        daily_rows = session.execute(
            select(PortfolioSnapshot).where(
                PortfolioSnapshot.account_id.in_(account_ids),
                PortfolioSnapshot.snapshot_date == date.today(),
            )
        ).scalars().all()

    daily_change = sum(
        (row.daily_change or Decimal("0") for row in daily_rows),
        Decimal("0"),
    )
    daily_percent = (
        (daily_change / (total_value - daily_change) * Decimal("100"))
        if total_value and total_value != daily_change
        else None
    )

    consolidated = session.scalar(
        select(PortfolioSnapshot)
        .where(
            PortfolioSnapshot.account_id.is_(None),
            PortfolioSnapshot.snapshot_date == date.today(),
        )
        .order_by(PortfolioSnapshot.id.desc())
        .limit(1)
    )

    tsx = consolidated.tsx_daily_change_percent if consolidated else None
    updated_at = consolidated.valuation_updated_at if consolidated else None

    brokerage_map: dict[str, dict[str, Decimal]] = {}
    account_rows = []
    for item in included:
        snapshot = next(
            (row for row in daily_rows if row.account_id == item.account_id),
            None,
        )
        account_daily_change = (
            snapshot.daily_change
            if snapshot and snapshot.daily_change is not None
            else None
        )
        account_rows.append({"summary": item, "daily_change": account_daily_change})

        bucket = brokerage_map.setdefault(
            item.brokerage_name,
            {"value": Decimal("0"), "daily_change": Decimal("0")},
        )
        bucket["value"] += item.current_value or Decimal("0")
        if account_daily_change is not None:
            bucket["daily_change"] += account_daily_change

    brokerages = [
        {"name": name, **values}
        for name, values in sorted(brokerage_map.items())
    ]

    return {
        "accounts": account_rows,
        "brokerages": brokerages,
        "total_value": total_value,
        "daily_change": daily_change,
        "daily_percent": daily_percent,
        "tsx": tsx,
        "updated_at": updated_at,
        "valuation_date": date.today(),
    }


@app.get("/snapshots", include_in_schema=False)
def web_manage_snapshots(
    request: Request,
    session: Annotated[Session, Depends(get_db)],
    account_key: str | None = Query(default=None),
    message: str = Query(default=""),
    message_class: str = Query(default=""),
):
    """Render imported brokerage snapshots and their external cash flows."""
    service = SnapshotManagementService(session)
    accounts = service.get_accounts()
    selected_account_id = None
    if account_key:
        for account in accounts:
            if account.key == account_key:
                selected_account_id = account.account_id
                break

    if selected_account_id is None and accounts:
        selected_account_id = accounts[0].account_id
        account_key = accounts[0].key

    snapshots = service.get_snapshots(selected_account_id)

    return templates.TemplateResponse(
        request=request,
        name="snapshots.html",
        context={
            "title": "Manage Snapshots",
            "description": (
                "Manage brokerage Excel snapshots. Daily portfolio updates do "
                "not create snapshots here."
            ),
            "navigation": NAVIGATION,
            "accounts": accounts,
            "account_key": account_key,
            "snapshots": snapshots,
            "message": message,
            "message_class": message_class,
        },
    )


@app.post("/snapshots/{snapshot_id}", include_in_schema=False)
def web_update_snapshot(
    snapshot_id: int,
    session: Annotated[Session, Depends(get_db)],
    external_added: str = Form(default="0"),
    external_withdrawn: str = Form(default="0"),
):
    """Update external cash flow amounts for one imported snapshot."""
    try:
        snapshot = SnapshotManagementService(session).update_cash_flow(
            snapshot_id,
            external_added,
            external_withdrawn,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    account = next(
        account
        for account in SnapshotManagementService(session).get_accounts()
        if account.account_id == snapshot.account_id
    )
    return RedirectResponse(
        url=(
            f"/snapshots?account_key={account.key}"
            "&message=Snapshot%20updated&message_class=success"
        ),
        status_code=303,
    )


@app.post("/import/snapshot/{snapshot_id}/cash-flow", include_in_schema=False)
def web_update_import_cash_flow(
    snapshot_id: int,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
    external_added: str = Form(default="0"),
    external_withdrawn: str = Form(default="0"),
):
    """Save cash-flow amounts directly from the completed import screen."""
    try:
        snapshot = SnapshotManagementService(session).update_cash_flow(
            snapshot_id,
            external_added,
            external_withdrawn,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return RedirectResponse(
        url=f"/snapshots?message=Snapshot%20updated&message_class=success",
        status_code=303,
    )


@app.get("/", include_in_schema=False)
def web_home() -> RedirectResponse:
    """Open the web application at the Portfolio page."""
    return RedirectResponse(url="/portfolio", status_code=307)


def _render_portfolio_page(
    request: Request,
    session: Session,
    *,
    message: str = "",
    message_class: str = "",
    tsx_override: Decimal | None = None,
):
    """Render the current Portfolio web page."""
    page = WEB_PAGES["/portfolio"]
    context = _portfolio_page_context(session)
    if tsx_override is not None:
        context["tsx"] = tsx_override
    return templates.TemplateResponse(
        request=request,
        name="portfolio.html",
        context={
            **page,
            **context,
            "navigation": NAVIGATION,
            "message": message,
            "message_class": message_class,
        },
    )


@app.get("/portfolio", include_in_schema=False)
def web_portfolio(
    request: Request,
    session: Annotated[Session, Depends(get_db)],
):
    """Render the current Portfolio web page from saved valuations."""
    return _render_portfolio_page(request, session)


@app.post("/portfolio/update", include_in_schema=False)
def web_portfolio_update(
    request: Request,
    session: Annotated[Session, Depends(get_db)],
    async_update: bool = Query(default=False),
):
    """Update portfolio values, optionally returning immediately for live progress."""
    if async_update:
        with _portfolio_update_lock:
            if _portfolio_update_state["running"]:
                return JSONResponse(
                    {"running": True, **_get_portfolio_update_state()},
                    status_code=409,
                )

            _portfolio_update_state.update(
                {
                    "running": True,
                    "count": 0,
                    "total": 0,
                    "symbol": "",
                    "percent": 0,
                    "message": "Preparing portfolio update...",
                    "error": False,
                }
            )

        thread = threading.Thread(
            target=_run_portfolio_update_background,
            name="web-portfolio-update",
            daemon=True,
        )
        thread.start()
        return JSONResponse(
            {"running": True, **_get_portfolio_update_state()},
            status_code=202,
        )

    try:
        from src.services.portfolio_valuation_service import PortfolioValuationService

        service = PortfolioValuationService(session)
        total_value = service.update_all_accounts()
        tsx_change = getattr(service, "tsx_daily_change_percent", None)
        context = _portfolio_page_context(session)
        if tsx_change is not None:
            context["tsx"] = tsx_change
        return templates.TemplateResponse(
            request=request,
            name="portfolio.html",
            context={
                **WEB_PAGES["/portfolio"],
                **context,
                "navigation": NAVIGATION,
                "message": f"Portfolio updated: ${total_value:,.2f}",
                "message_class": "positive",
            },
        )
    except Exception as exc:
        return _render_portfolio_page(
            request,
            session,
            message=f"Portfolio update failed: {type(exc).__name__}: {exc}",
            message_class="negative",
        )


@app.get("/portfolio/update-status", include_in_schema=False)
def web_portfolio_update_status():
    """Return the current background portfolio update progress."""
    return JSONResponse(_get_portfolio_update_state())


@app.post("/portfolio/update-tsx", include_in_schema=False)
def web_portfolio_update_tsx(
    request: Request,
    session: Annotated[Session, Depends(get_db)],
):
    """Retrieve the current TSX daily change without updating the portfolio."""
    try:
        from src.services.market_price_service import MarketPriceService

        price = MarketPriceService().get_price("^GSPTSE")
        if price is None or price.change_percent is None:
            raise ValueError("Could not retrieve the TSX Composite daily change.")
        return _render_portfolio_page(
            request,
            session,
            message=f"TSX updated: {price.change_percent:+.2f}%",
            message_class="positive",
            tsx_override=price.change_percent,
        )
    except Exception as exc:
        return _render_portfolio_page(
            request,
            session,
            message=f"TSX update failed: {type(exc).__name__}: {exc}",
            message_class="negative",
        )



@app.get("/portfolio/history", include_in_schema=False)
def web_portfolio_history(
    request: Request,
    session: Annotated[Session, Depends(get_db)],
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    account_keys: list[str] | None = Query(default=None),
    view: str = Query(default="Portfolio Value"),
    benchmark: str = Query(default=DEFAULT_BENCHMARK),
    custom_benchmark: str = Query(default=""),
    brokerage_lines: list[str] | None = Query(default=None),
):
    """Render Portfolio History using the existing history services."""
    return _render_history_page(
        request,
        session,
        page_type="portfolio",
        start_date=start_date,
        end_date=end_date,
        selected_keys=account_keys,
        view=view,
        benchmark=benchmark,
        custom_benchmark=custom_benchmark,
        brokerage_lines=brokerage_lines,
    )


@app.get("/accounts/history", include_in_schema=False)
def web_account_history(
    request: Request,
    session: Annotated[Session, Depends(get_db)],
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    account_keys: list[str] | None = Query(default=None),
    view: str = Query(default="Portfolio Value"),
    benchmark: str = Query(default=DEFAULT_BENCHMARK),
    custom_benchmark: str = Query(default=""),
):
    """Render Account History using the existing comparison history service."""
    return _render_history_page(
        request,
        session,
        page_type="account",
        start_date=start_date,
        end_date=end_date,
        selected_keys=account_keys,
        view=view,
        benchmark=benchmark,
        custom_benchmark=custom_benchmark,
    )


@app.get("/import", include_in_schema=False)
def web_import_page(
    request: Request,
):
    """Render the brokerage import page."""
    return templates.TemplateResponse(
        request=request,
        name="import.html",
        context={
            "title": "Import",
            "description": "Upload a brokerage Excel snapshot and import it into the financial model.",
            "navigation": NAVIGATION,
            "result": None,
            "error": None,
        },
    )


def _import_upload(
    session: Session,
    brokerage: str,
    upload: UploadFile,
):
    """Process one uploaded brokerage workbook using the existing importer and ImportService."""
    filename = Path(upload.filename or "").name
    suffix = Path(filename).suffix.lower()
    if suffix not in {".xlsx", ".xlsm"}:
        raise HTTPException(
            status_code=400,
            detail="Only .xlsx and .xlsm Excel files are supported.",
        )

    importer_class = {
        "BMO": BMOImporter,
        "Nesbitt Burns": NesbittImporter,
    }.get(brokerage)
    if importer_class is None:
        raise HTTPException(status_code=400, detail="Unsupported brokerage.")

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=suffix,
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            while True:
                chunk = upload.file.read(1024 * 1024)
                if not chunk:
                    break
                temp_file.write(chunk)

        imported_account = importer_class(temp_path).import_file()
        return ImportService(session).import_snapshot(
            brokerage_name=brokerage,
            imported_account=imported_account,
            file_name=filename,
        )
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


@app.post("/import", include_in_schema=False)
def web_import(
    request: Request,
    session: Annotated[Session, Depends(get_db)],
    brokerage: str = Form(...),
    upload: UploadFile = File(...),
):
    """Import one uploaded brokerage workbook and render the result."""
    try:
        result = _import_upload(session, brokerage, upload)
    except HTTPException:
        raise
    except Exception as exc:
        session.rollback()
        return templates.TemplateResponse(
            request=request,
            name="import.html",
            status_code=400,
            context={
                "title": "Import",
                "description": "Upload a brokerage Excel snapshot and import it into the financial model.",
                "navigation": NAVIGATION,
                "result": None,
                "error": f"{type(exc).__name__}: {exc}",
            },
        )

    return templates.TemplateResponse(
        request=request,
        name="import.html",
        context={
            "title": "Import",
            "description": "Upload a brokerage Excel snapshot and import it into the financial model.",
            "navigation": NAVIGATION,
            "result": result,
            "error": None,
        },
    )


@app.get("/accounts", include_in_schema=False)
def web_accounts(
    request: Request,
    session: Annotated[Session, Depends(get_db)],
):
    """Render Account Management using AccountService."""
    summaries = AccountService(session).get_summaries()
    return templates.TemplateResponse(
        request=request,
        name="accounts.html",
        context={
            "title": "Account Management",
            "description": "Manage account names, classification, portfolio inclusion, and current account information.",
            "navigation": NAVIGATION,
            "accounts": summaries,
            "account_types": getattr(AccountService, "ACCOUNT_TYPES", ()),
        },
    )


@app.post("/accounts/{account_id}/rename", include_in_schema=False)
def web_rename_account(
    account_id: int,
    session: Annotated[Session, Depends(get_db)],
    name: str = Form(...),
):
    """Rename an account through AccountService."""
    try:
        AccountService(session).rename(account_id, name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse("/accounts", status_code=303)


@app.post("/accounts/{account_id}/settings", include_in_schema=False)
def web_account_settings(
    account_id: int,
    session: Annotated[Session, Depends(get_db)],
    account_type: str = Form(default=""),
    include_in_portfolio: bool = Form(default=False),
):
    """Save account classification and portfolio inclusion through AccountService."""
    try:
        AccountService(session).update_settings(
            account_id=account_id,
            account_type=account_type.strip() or None,
            include_in_portfolio=include_in_portfolio,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse("/accounts", status_code=303)


@app.get("/holdings/history", include_in_schema=False)
def web_holdings_history(
    request: Request,
    session: Annotated[Session, Depends(get_db)],
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    account_key: str | None = Query(default=None),
):
    """Render holdings history by comparing two dates for one account."""
    start, end = _date_range(from_date, to_date)
    accounts = _history_accounts(session)
    selected = next(
        (item for item in accounts if item["key"] == account_key),
        accounts[0] if accounts else None,
    )

    comparison = None
    if selected is not None:
        comparison = PortfolioComparisonService(session).compare(
            start,
            end,
            account_id=int(selected["id"]),
        )

    return templates.TemplateResponse(
        request=request,
        name="holdings_history.html",
        context={
            "title": "Holdings History",
            "description": "Compare holdings between two dates.",
            "navigation": NAVIGATION,
            "accounts": accounts,
            "selected_key": selected["key"] if selected else None,
            "from_date": start.isoformat(),
            "to_date": end.isoformat(),
            "comparison": comparison,
        },
    )


def _render_web_page(request: Request, path: str):
    """Render one page from the common responsive web shell."""
    page = WEB_PAGES[path]
    return templates.TemplateResponse(
        request=request,
        name="page.html",
        context={**page, "navigation": NAVIGATION},
    )


def _make_web_handler(path: str):
    """Create a FastAPI handler for one shell page."""
    def handler(request: Request):
        return _render_web_page(request, path)

    return handler


for _path in WEB_PAGES:
    if _path in {"/portfolio", "/accounts", "/import"}:
        continue
    app.add_api_route(
        _path,
        _make_web_handler(_path),
        methods=["GET"],
        include_in_schema=False,
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    """Return the API health status."""
    return {"status": "ok"}


@app.get("/api/accounts", response_model=list[AccountSummaryResponse])
def get_accounts(
    session: Annotated[Session, Depends(get_db)],
) -> list[AccountSummaryResponse]:
    """Return account summaries using the existing AccountService."""
    summaries = AccountService(session).get_summaries()
    return [
        AccountSummaryResponse(
            account_id=item.account_id,
            brokerage_name=item.brokerage_name,
            account_number=item.account_number,
            name=item.name,
            account_type=item.account_type,
            include_in_portfolio=item.include_in_portfolio,
            current_value=_decimal(item.current_value),
            cash_by_currency={currency: str(amount) for currency, amount in item.cash_by_currency.items()},
            holdings_count=item.holdings_count,
            last_import=_date(item.last_import),
        )
        for item in summaries
    ]


@app.get("/api/portfolio/history", response_model=list[PortfolioHistoryPointResponse])
def get_portfolio_history(
    session: Annotated[Session, Depends(get_db)],
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    account_ids: list[int] | None = Query(default=None),
) -> list[PortfolioHistoryPointResponse]:
    """Return aggregated portfolio history for selected accounts."""
    start, end = _date_range(start_date, end_date)
    selected_ids = account_ids
    if selected_ids is None:
        selected_ids = [account.id for account in AccountService(session).get_all()]

    points = PortfolioHistoryService(session).get_aggregated_history(start, end, selected_ids)
    return [
        PortfolioHistoryPointResponse(
            snapshot_date=point.snapshot_date.isoformat(),
            total_value=str(point.total_value),
        )
        for point in points
    ]


@app.get("/api/portfolio/{account_id}", response_model=PortfolioResponse)
def get_portfolio(
    account_id: int,
    session: Annotated[Session, Depends(get_db)],
) -> PortfolioResponse:
    """Return the latest imported portfolio for an account."""
    portfolio = PortfolioService(session).get_latest_portfolio(account_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail=f"No imported portfolio exists for account {account_id}.")

    return PortfolioResponse(
        account_id=portfolio.account_id,
        snapshot_date=portfolio.snapshot_date.isoformat(),
        holdings=[
            PortfolioHoldingResponse(
                snapshot_id=item.snapshot_id,
                symbol=item.symbol,
                company_name=item.company_name,
                quantity=str(item.quantity),
                price=str(item.price),
                market_value=str(item.market_value),
                average_cost=str(item.average_cost),
                unrealized_gain=str(item.unrealized_gain),
                unrealized_gain_percent=_decimal(item.unrealized_gain_percent),
                daily_change=_decimal(item.daily_change),
                daily_change_percent=_decimal(item.daily_change_percent),
                previous_close=_decimal(item.previous_close),
                current_price=_decimal(item.current_price),
                current_market_value=_decimal(item.current_market_value),
                current_previous_close=_decimal(item.current_previous_close),
                current_daily_change=_decimal(item.current_daily_change),
                current_daily_change_percent=_decimal(item.current_daily_change_percent),
                currency=item.currency,
            )
            for item in portfolio.holdings
        ],
        cash=[PortfolioCashResponse(currency=item.currency, amount=str(item.amount)) for item in portfolio.cash],
    )


@app.get("/api/holdings", response_model=list[PortfolioResponse])
def get_holdings(
    session: Annotated[Session, Depends(get_db)],
    account_id: int | None = Query(default=None),
) -> list[PortfolioResponse]:
    """Return latest holdings, optionally limited to one account."""
    account_service = AccountService(session)
    account_ids = [account_id] if account_id is not None else [account.id for account in account_service.get_all()]
    result: list[PortfolioResponse] = []
    portfolio_service = PortfolioService(session)
    for selected_account_id in account_ids:
        portfolio = portfolio_service.get_latest_portfolio(selected_account_id)
        if portfolio is None:
            continue
        result.append(
            PortfolioResponse(
                account_id=portfolio.account_id,
                snapshot_date=portfolio.snapshot_date.isoformat(),
                holdings=[
                    PortfolioHoldingResponse(
                        snapshot_id=item.snapshot_id,
                        symbol=item.symbol,
                        company_name=item.company_name,
                        quantity=str(item.quantity),
                        price=str(item.price),
                        market_value=str(item.market_value),
                        average_cost=str(item.average_cost),
                        unrealized_gain=str(item.unrealized_gain),
                        unrealized_gain_percent=_decimal(item.unrealized_gain_percent),
                        daily_change=_decimal(item.daily_change),
                        daily_change_percent=_decimal(item.daily_change_percent),
                        previous_close=_decimal(item.previous_close),
                        current_price=_decimal(item.current_price),
                        current_market_value=_decimal(item.current_market_value),
                        current_previous_close=_decimal(item.current_previous_close),
                        current_daily_change=_decimal(item.current_daily_change),
                        current_daily_change_percent=_decimal(item.current_daily_change_percent),
                        currency=item.currency,
                    )
                    for item in portfolio.holdings
                ],
                cash=[PortfolioCashResponse(currency=item.currency, amount=str(item.amount)) for item in portfolio.cash],
            )
        )
    if account_id is not None and not result:
        raise HTTPException(status_code=404, detail=f"No imported portfolio exists for account {account_id}.")
    return result


@app.get("/api/accounts/{account_id}/history", response_model=list[AccountHistoryPointResponse])
def get_account_history(
    account_id: int,
    session: Annotated[Session, Depends(get_db)],
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
) -> list[AccountHistoryPointResponse]:
    """Return historical valuations for one account."""
    start, end = _date_range(start_date, end_date)
    if AccountService(session).get(account_id) is None:
        raise HTTPException(status_code=404, detail="Account not found.")
    histories = AccountComparisonHistoryService(session).get_histories([account_id], start, end)
    return [
        AccountHistoryPointResponse(
            account_id=point.account_id,
            snapshot_date=point.snapshot_date.isoformat(),
            total_value=str(point.total_value),
        )
        for point in histories.get(account_id, [])
    ]
