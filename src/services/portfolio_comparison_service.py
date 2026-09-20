from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.models.account import Account
from src.models.brokerage import Brokerage
from src.models.company import Company
from src.models.holding_snapshot import HoldingSnapshot
from src.models.import_record import ImportRecord
from src.models.portfolio_snapshot import PortfolioSnapshot

ZERO = Decimal("0")

@dataclass
class PositionComparison:
    symbol: str
    company_name: str
    first_quantity: Decimal
    second_quantity: Decimal
    quantity_difference: Decimal
    first_average_cost: Decimal | None
    second_average_cost: Decimal | None
    first_market_value: Decimal | None
    second_market_value: Decimal | None
    first_unrealized_gain: Decimal | None
    second_unrealized_gain: Decimal | None
    currency: str
    status: str

@dataclass
class PortfolioComparison:
    first_value: Decimal | None
    second_value: Decimal | None
    value_difference: Decimal | None
    positions: list[PositionComparison]

@dataclass
class ComparisonAccount:
    account_id: int
    brokerage_name: str
    account_number: str
    account_name: str

class PortfolioComparisonService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_accounts(self) -> list[ComparisonAccount]:
        rows = self.session.execute(
            select(Account, Brokerage)
            .join(Brokerage, Brokerage.id == Account.brokerage_id)
            .order_by(Brokerage.name, Account.account_number)
        ).all()
        return [
            ComparisonAccount(
                account_id=a.id,
                brokerage_name=b.name,
                account_number=str(a.account_number),
                account_name=str(a.name or ""),
            )
            for a, b in rows
        ]

    def compare(
        self,
        first_date: date,
        second_date: date,
        account_id: int | None = None,
        *,
        account_ids: list[int] | None = None,
    ) -> PortfolioComparison:
        """Compare holdings for one, several, or all accounts.

        ``account_id`` is retained for backwards compatibility.  New callers
        that need multi-account selection should pass ``account_ids``.
        """
        selected_ids = self._resolve_account_ids(account_id, account_ids)

        first_value = self._get_portfolio_value(first_date, selected_ids)
        second_value = self._get_portfolio_value(second_date, selected_ids)
        difference = (
            second_value - first_value
            if first_value is not None and second_value is not None
            else None
        )

        first = self._get_selected_positions(first_date, selected_ids)
        second = self._get_selected_positions(second_date, selected_ids)

        return PortfolioComparison(
            first_value=first_value,
            second_value=second_value,
            value_difference=difference,
            positions=self._build_comparison(first, second),
        )

    def _resolve_account_ids(
        self,
        account_id: int | None,
        account_ids: list[int] | None,
    ) -> list[int]:
        if account_ids is not None:
            return list(dict.fromkeys(account_ids))
        if account_id is not None:
            return [account_id]
        return [account.account_id for account in self.get_accounts()]

    def _get_portfolio_value(
        self,
        requested_date: date,
        account_ids: list[int],
    ) -> Decimal | None:
        total = ZERO
        found = False

        for account_id in account_ids:
            row = self.session.scalar(
                select(PortfolioSnapshot)
                .where(
                    PortfolioSnapshot.account_id == account_id,
                    PortfolioSnapshot.snapshot_date <= requested_date,
                )
                .order_by(PortfolioSnapshot.snapshot_date.desc())
                .limit(1)
            )
            if row is not None:
                total += Decimal(str(row.total_value))
                found = True

        return total if found else None

    def _get_selected_positions(
        self,
        requested_date: date,
        account_ids: list[int],
    ) -> dict[str, dict]:
        result = {}
        for account_id in account_ids:
            positions = self._get_positions(
                account_id,
                self._get_snapshot_date(account_id, requested_date),
            )
            self._merge_positions(result, positions)

        self._finalize_positions(result)
        return result

    def _merge_positions(
        self,
        result: dict[str, dict],
        positions: dict[str, dict],
    ) -> None:
        for symbol, position in positions.items():
            if position["quantity"] == 0:
                continue

            current = result.setdefault(
                symbol,
                {
                    "company_name": position["company_name"],
                    "quantity": ZERO,
                    "cost_total": ZERO,
                    "market_value": ZERO,
                    "unrealized_gain": ZERO,
                    "currency": position["currency"],
                    "has_cost": False,
                    "has_mv": False,
                    "has_gain": False,
                },
            )

            quantity = position["quantity"]
            current["quantity"] += quantity

            if position["average_cost"] is not None:
                current["cost_total"] += quantity * position["average_cost"]
                current["has_cost"] = True
            if position["market_value"] is not None:
                current["market_value"] += position["market_value"]
                current["has_mv"] = True
            if position["unrealized_gain"] is not None:
                current["unrealized_gain"] += position["unrealized_gain"]
                current["has_gain"] = True

    @staticmethod
    def _finalize_positions(result: dict[str, dict]) -> None:
        for position in result.values():
            position["average_cost"] = (
                position["cost_total"] / position["quantity"]
                if position["has_cost"] and position["quantity"] != 0
                else None
            )
            if not position["has_mv"]:
                position["market_value"] = None
            if not position["has_gain"]:
                position["unrealized_gain"] = None

            for key in ("cost_total", "has_cost", "has_mv", "has_gain"):
                position.pop(key, None)

    def _get_snapshot_date(self, account_id: int,
                           requested_date: date) -> datetime | None:
        end = datetime.combine(requested_date + timedelta(days=1), time.min)
        row = self.session.scalar(
            select(ImportRecord)
            .where(
                ImportRecord.account_id == account_id,
                ImportRecord.snapshot_date < end,
            )
            .order_by(ImportRecord.snapshot_date.desc())
            .limit(1)
        )
        return None if row is None else row.snapshot_date

    @staticmethod
    def _rows_to_positions(rows) -> dict[str, dict]:
        result = {}
        for symbol, name, qty, avg, mv, gain, currency in rows:
            result[symbol] = {
                "company_name": name,
                "quantity": Decimal(str(qty)),
                "average_cost": None if avg is None else Decimal(str(avg)),
                "market_value": None if mv is None else Decimal(str(mv)),
                "unrealized_gain": None if gain is None else Decimal(str(gain)),
                "currency": currency or "",
            }
        return result

    def _get_positions(self, account_id: int,
                       snapshot_date: datetime | None) -> dict[str, dict]:
        if snapshot_date is None:
            return {}
        rows = self.session.execute(
            select(
                Company.symbol, Company.name, HoldingSnapshot.quantity,
                HoldingSnapshot.average_cost, HoldingSnapshot.market_value,
                HoldingSnapshot.unrealized_gain, HoldingSnapshot.currency,
            )
            .join(HoldingSnapshot, HoldingSnapshot.company_id == Company.id)
            .where(
                HoldingSnapshot.account_id == account_id,
                HoldingSnapshot.snapshot_date == snapshot_date,
            )
        ).all()
        return self._rows_to_positions(rows)

    def _get_consolidated_positions(self, requested_date: date) -> dict[str, dict]:
        result = {}
        for account in self.get_accounts():
            positions = self._get_positions(
                account.account_id,
                self._get_snapshot_date(account.account_id, requested_date),
            )
            for symbol, p in positions.items():
                if p["quantity"] == 0:
                    continue
                x = result.setdefault(symbol, {
                    "company_name": p["company_name"],
                    "quantity": ZERO,
                    "cost_total": ZERO,
                    "market_value": ZERO,
                    "unrealized_gain": ZERO,
                    "currency": p["currency"],
                    "has_cost": False,
                    "has_mv": False,
                    "has_gain": False,
                })
                q = p["quantity"]
                x["quantity"] += q
                if p["average_cost"] is not None:
                    x["cost_total"] += q * p["average_cost"]
                    x["has_cost"] = True
                if p["market_value"] is not None:
                    x["market_value"] += p["market_value"]
                    x["has_mv"] = True
                if p["unrealized_gain"] is not None:
                    x["unrealized_gain"] += p["unrealized_gain"]
                    x["has_gain"] = True
        for x in result.values():
            x["average_cost"] = (
                x["cost_total"] / x["quantity"]
                if x["has_cost"] and x["quantity"] != 0 else None
            )
            if not x["has_mv"]:
                x["market_value"] = None
            if not x["has_gain"]:
                x["unrealized_gain"] = None
            for key in ("cost_total", "has_cost", "has_mv", "has_gain"):
                x.pop(key, None)
        return result

    @staticmethod
    def _status(q1: Decimal, q2: Decimal) -> str:
        p1, p2 = q1 != 0, q2 != 0
        if not p1 and p2: return "New"
        if p1 and not p2: return "Sold"
        if q2 > q1: return "Increased"
        if q2 < q1: return "Decreased"
        return "Unchanged"

    def _build_comparison(self, first: dict, second: dict) -> list[PositionComparison]:
        result = []
        for symbol in sorted(set(first) | set(second)):
            a, b = first.get(symbol), second.get(symbol)
            source = b or a
            q1 = a["quantity"] if a else ZERO
            q2 = b["quantity"] if b else ZERO
            result.append(PositionComparison(
                symbol=symbol,
                company_name=source["company_name"],
                first_quantity=q1,
                second_quantity=q2,
                quantity_difference=q2 - q1,
                first_average_cost=a["average_cost"] if a else None,
                second_average_cost=b["average_cost"] if b else None,
                first_market_value=a["market_value"] if a else None,
                second_market_value=b["market_value"] if b else None,
                first_unrealized_gain=a["unrealized_gain"] if a else None,
                second_unrealized_gain=b["unrealized_gain"] if b else None,
                currency=source["currency"],
                status=self._status(q1, q2),
            ))
        return result
