"""FastAPI application entry point for the Financial Model."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy.orm import Session

from src.database import get_session
from src.services.account_comparison_history_service import (
    AccountComparisonHistoryService,
)
from src.services.account_service import AccountService
from src.services.portfolio_history_service import PortfolioHistoryService
from src.services.portfolio_service import PortfolioService
from src.api.schemas import (
    AccountHistoryPointResponse,
    AccountSummaryResponse,
    PortfolioCashResponse,
    PortfolioHistoryPointResponse,
    PortfolioHoldingResponse,
    PortfolioResponse,
)

app = FastAPI(
    title="Davison Financial Model API",
    version="0.2.0",
)


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
            cash_by_currency={
                currency: str(amount)
                for currency, amount in item.cash_by_currency.items()
            },
            holdings_count=item.holdings_count,
            last_import=_date(item.last_import),
        )
        for item in summaries
    ]


@app.get(
    "/api/portfolio/history",
    response_model=list[PortfolioHistoryPointResponse],
)
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

    points = PortfolioHistoryService(session).get_aggregated_history(
        start,
        end,
        selected_ids,
    )
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
        raise HTTPException(
            status_code=404,
            detail=f"No imported portfolio exists for account {account_id}.",
        )

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
                current_daily_change_percent=_decimal(
                    item.current_daily_change_percent
                ),
                currency=item.currency,
            )
            for item in portfolio.holdings
        ],
        cash=[
            PortfolioCashResponse(
                currency=item.currency,
                amount=str(item.amount),
            )
            for item in portfolio.cash
        ],
    )


@app.get("/api/holdings", response_model=list[PortfolioResponse])
def get_holdings(
    session: Annotated[Session, Depends(get_db)],
    account_id: int | None = Query(default=None),
) -> list[PortfolioResponse]:
    """Return latest holdings, optionally limited to one account."""
    account_service = AccountService(session)
    account_ids = (
        [account_id]
        if account_id is not None
        else [account.id for account in account_service.get_all()]
    )

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
                        unrealized_gain_percent=_decimal(
                            item.unrealized_gain_percent
                        ),
                        daily_change=_decimal(item.daily_change),
                        daily_change_percent=_decimal(item.daily_change_percent),
                        previous_close=_decimal(item.previous_close),
                        current_price=_decimal(item.current_price),
                        current_market_value=_decimal(item.current_market_value),
                        current_previous_close=_decimal(
                            item.current_previous_close
                        ),
                        current_daily_change=_decimal(item.current_daily_change),
                        current_daily_change_percent=_decimal(
                            item.current_daily_change_percent
                        ),
                        currency=item.currency,
                    )
                    for item in portfolio.holdings
                ],
                cash=[
                    PortfolioCashResponse(
                        currency=item.currency,
                        amount=str(item.amount),
                    )
                    for item in portfolio.cash
                ],
            )
        )

    if account_id is not None and not result:
        raise HTTPException(
            status_code=404,
            detail=f"No imported portfolio exists for account {account_id}.",
        )

    return result


@app.get(
    "/api/accounts/{account_id}/history",
    response_model=list[AccountHistoryPointResponse],
)
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
    histories = AccountComparisonHistoryService(session).get_histories(
        [account_id],
        start,
        end,
    )
    return [
        AccountHistoryPointResponse(
            account_id=point.account_id,
            snapshot_date=point.snapshot_date.isoformat(),
            total_value=str(point.total_value),
        )
        for point in histories.get(account_id, [])
    ]
