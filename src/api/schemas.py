"""JSON DTOs used by the Financial Model web API."""

from __future__ import annotations

from pydantic import BaseModel


class AccountSummaryResponse(BaseModel):
    account_id: int
    brokerage_name: str
    account_number: str
    name: str
    account_type: str | None
    include_in_portfolio: bool
    current_value: str | None
    cash_by_currency: dict[str, str]
    holdings_count: int
    last_import: str | None


class PortfolioHoldingResponse(BaseModel):
    snapshot_id: int
    symbol: str
    company_name: str
    quantity: str
    price: str
    market_value: str
    average_cost: str
    unrealized_gain: str
    unrealized_gain_percent: str | None
    daily_change: str | None
    daily_change_percent: str | None
    previous_close: str | None
    current_price: str | None
    current_market_value: str | None
    current_previous_close: str | None
    current_daily_change: str | None
    current_daily_change_percent: str | None
    currency: str


class PortfolioCashResponse(BaseModel):
    currency: str
    amount: str


class PortfolioResponse(BaseModel):
    account_id: int
    snapshot_date: str
    holdings: list[PortfolioHoldingResponse]
    cash: list[PortfolioCashResponse]


class PortfolioHistoryPointResponse(BaseModel):
    snapshot_date: str
    total_value: str


class AccountHistoryPointResponse(BaseModel):
    account_id: int
    snapshot_date: str
    total_value: str
