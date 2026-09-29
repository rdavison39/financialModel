"""FastAPI application entry point for the Financial Model."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
import tempfile
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import RedirectResponse
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
from src.models.account import Account
from src.models.portfolio_snapshot import PortfolioSnapshot
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
    start_date: date,
    end_date: date,
) -> list[dict[str, object]]:
    """Build the selected benchmark series for percentage views."""
    symbol = _benchmark_symbol(benchmark_name, custom_symbol)
    if not symbol or not _is_percent_view(view):
        return []

    query_start = start_date
    if view == "% Day's Gain/Loss":
        query_start = start_date - timedelta(days=14)

    try:
        points = service.get_benchmark_history(symbol, query_start, end_date)
    except Exception:
        return []

    if view == "% Growth Since Start":
        points = [point for point in points if point.snapshot_date >= start_date]
        if not points:
            return []
        first = points[0].value
        values = [
            Decimal("0")
            if first == 0
            else (point.value - first) / first * Decimal("100")
            for point in points
        ]
    else:
        prior = None
        for point in points:
            if point.snapshot_date < start_date:
                prior = point.value
        values = []
        plotted = []
        for point in points:
            if point.snapshot_date < start_date:
                continue
            if prior is None or prior == 0:
                value = None
            else:
                value = (point.value - prior) / prior * Decimal("100")
            prior = point.value
            if value is not None:
                plotted.append(point.snapshot_date)
                values.append(value)
        return [
            {"date": point.isoformat(), "value": str(value)}
            for point, value in zip(plotted, values)
        ]

    return [
        {"date": point.snapshot_date.isoformat(), "value": str(value)}
        for point, value in zip(points, values)
    ]


def _portfolio_history_series(
    points,
    view: str,
    trading_dates: set[date],
) -> list[dict[str, object]]:
    """Transform portfolio history points into a chart series."""
    if view == "Portfolio Value":
        selected = points
        return [
            {"date": point.snapshot_date.isoformat(), "value": str(point.total_value)}
            for point in selected
        ]

    selected = [point for point in points if point.snapshot_date in trading_dates]
    if view == "% Growth Since Start":
        if not selected:
            return []
        first = selected[0].total_value
        return [
            {
                "date": point.snapshot_date.isoformat(),
                "value": str(
                    Decimal("0")
                    if first == 0
                    else (point.total_value - first) / first * Decimal("100")
                ),
            }
            for point in selected
        ]

    return [
        {
            "date": point.snapshot_date.isoformat(),
            "value": str(
                point.daily_change
                if view == "Day's Gain/Loss"
                else point.daily_change_percent
            )
            if (
                point.daily_change
                if view == "Day's Gain/Loss"
                else point.daily_change_percent
            )
            is not None
            else None,
        }
        for point in selected
    ]


def _account_history_series(
    history: dict[int, list],
    account_labels: dict[int, str],
    view: str,
    trading_dates: set[date],
) -> list[dict[str, object]]:
    """Transform selected account histories into chart series."""
    result = []
    for account_id, points in history.items():
        if view == "Portfolio Value":
            selected = points
        else:
            selected = [point for point in points if point.snapshot_date in trading_dates]

        if view == "% Growth Since Start":
            if not selected:
                continue
            first = selected[0].total_value
            values = [
                Decimal("0")
                if first == 0
                else (point.total_value - first) / first * Decimal("100")
                for point in selected
            ]
        elif view == "Day's Gain/Loss":
            values = [point.daily_change for point in selected]
        elif view == "% Day's Gain/Loss":
            values = [point.daily_change_percent for point in selected]
        else:
            values = [point.total_value for point in selected]

        result.append(
            {
                "label": account_labels[account_id],
                "points": [
                    {"date": point.snapshot_date.isoformat(), "value": str(value)}
                    for point, value in zip(selected, values)
                    if value is not None
                ],
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
):
    """Build and render the common portfolio/account history page."""
    start, end = _date_range(start_date, end_date)
    if view not in HISTORY_VIEWS:
        view = "Portfolio Value"
    if benchmark not in BENCHMARKS:
        benchmark = DEFAULT_BENCHMARK
    if not _is_percent_view(view):
        benchmark = "None"

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
        table_rows = [
            {
                "date": point.snapshot_date,
                "value": (
                    point.total_value
                    if view == "Portfolio Value"
                    else point.daily_change
                    if view == "Day's Gain/Loss"
                    else point.daily_change_percent
                    if view == "% Day's Gain/Loss"
                    else (
                        Decimal("0")
                        if point.total_value == 0
                        else (point.total_value - points[0].total_value)
                        / points[0].total_value
                        * Decimal("100")
                    )
                ),
            }
            for point in points
            if view == "Portfolio Value" or point.snapshot_date in trading_dates
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
            for point in points:
                if view != "Portfolio Value" and point.snapshot_date not in trading_dates:
                    continue
                if view == "Portfolio Value":
                    value = point.total_value
                elif view == "% Growth Since Start":
                    account_points = [
                        item for item in points if item.snapshot_date in trading_dates
                    ]
                    first = account_points[0].total_value if account_points else None
                    value = (
                        None
                        if first is None or first == 0
                        else (point.total_value - first) / first * Decimal("100")
                    )
                elif view == "Day's Gain/Loss":
                    value = point.daily_change
                else:
                    value = point.daily_change_percent
                if value is not None:
                    table_rows.append(
                        {
                            "date": point.snapshot_date,
                            "label": labels.get(account_id, str(account_id)),
                            "value": value,
                        }
                    )

    benchmark_series = _benchmark_series(
        history_service,
        benchmark,
        custom_benchmark,
        view,
        start,
        end,
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


@app.get("/", include_in_schema=False)
def web_home() -> RedirectResponse:
    """Open the web application at the Portfolio page."""
    return RedirectResponse(url="/portfolio", status_code=307)


@app.get("/portfolio", include_in_schema=False)
def web_portfolio(
    request: Request,
    session: Annotated[Session, Depends(get_db)],
):
    """Render the current Portfolio web page from saved valuations."""
    page = WEB_PAGES["/portfolio"]
    context = _portfolio_page_context(session)
    return templates.TemplateResponse(
        request=request,
        name="portfolio.html",
        context={**page, **context, "navigation": NAVIGATION},
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
