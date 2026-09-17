"""
Portfolio tab for the Financial Model GUI.
"""

import tkinter as tk
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from tkinter import messagebox, simpledialog, ttk

from sqlalchemy import select, func

from src.database import get_session
from src.database_init import initialize_database
from src.models.account import Account
from src.models.brokerage import Brokerage
from src.models.portfolio_snapshot import PortfolioSnapshot
from src.models.holding_snapshot import HoldingSnapshot
from src.services.portfolio_service import PortfolioService
from src.services.portfolio_valuation_service import (
    PortfolioValuationService,
)


class PortfolioTab(ttk.Frame):
    """Display current portfolio values."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(5, weight=1)

        self._build_ui()

        # Load existing values when the tab is created.
        self.after(100, self._load_current_values)

    # =============================================================
    # UI
    # =============================================================

    def _build_ui(self) -> None:
        """Build the portfolio page."""

        ttk.Label(
            self,
            text="Portfolio",
            font=("Segoe UI", 18, "bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 15),
        )

        # ---------------------------------------------------------
        # Controls
        # ---------------------------------------------------------

        controls = ttk.Frame(self)

        controls.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(0, 10),
        )

        ttk.Button(
            controls,
            text="Update Portfolio",
            command=self._update_portfolio,
        ).pack(side="left")

        self.status_label = ttk.Label(
            controls,
            text="",
        )

        self.status_label.pack(
            side="left",
            padx=15,
        )

        # ---------------------------------------------------------
        # Update progress
        # ---------------------------------------------------------

        # Keep update progress on one line.  The valuation service
        # reports the current symbol and X/Y count through the
        # progress callback below.
        self.progress_frame = ttk.Frame(self)

        self.progress_frame.grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(0, 15),
        )

        self.progress_frame.columnconfigure(1, weight=1)

        self.progress_label = ttk.Label(
            self.progress_frame,
            text="Ready",
            font=("Consolas", 10),
        )

        self.progress_label.grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 10),
        )

        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            orient="horizontal",
            mode="determinate",
            maximum=100,
            length=300,
        )

        self.progress_bar.grid(
            row=0,
            column=1,
            sticky="ew",
        )

        # ---------------------------------------------------------
        # Portfolio summary
        # ---------------------------------------------------------

        summary = ttk.LabelFrame(
            self,
            text="Portfolio Summary",
            padding=12,
        )

        summary.grid(
            row=3,
            column=0,
            sticky="ew",
            pady=(0, 15),
        )

        summary.columnconfigure(0, weight=1)
        summary.columnconfigure(1, weight=1)
        summary.columnconfigure(2, weight=1)

        # Total portfolio

        ttk.Label(
            summary,
            text="Total Portfolio:",
            font=("Segoe UI", 12, "bold"),
        ).grid(
            row=0,
            column=0,
            sticky="e",
            padx=(10, 5),
        )

        self.total_value_label = ttk.Label(
            summary,
            text="$0.00",
            font=("Segoe UI", 14, "bold"),
        )

        self.total_value_label.grid(
            row=0,
            column=1,
            sticky="w",
            padx=5,
        )

        # Today

        self.total_change_label = ttk.Label(
            summary,
            text="Today: --",
            font=("Segoe UI", 12, "bold"),
        )

        self.total_change_label.grid(
            row=0,
            column=2,
            sticky="w",
            padx=(15, 5),
        )

        # TSX

        self.tsx_label = ttk.Label(
            summary,
            text="TSX: --",
            font=("Segoe UI", 12, "bold"),
        )

        self.tsx_label.grid(
            row=0,
            column=3,
            sticky="w",
            padx=(15, 10),
        )

        # ---------------------------------------------------------
        # Brokerage summary
        # ---------------------------------------------------------

        brokerage_frame = ttk.LabelFrame(
            self,
            text="Brokerage Summary",
            padding=8,
        )

        brokerage_frame.grid(
            row=4,
            column=0,
            sticky="ew",
            pady=(0, 15),
        )

        brokerage_frame.columnconfigure(0, weight=1)

        self.brokerage_tree = ttk.Treeview(
            brokerage_frame,
            columns=(
                "brokerage",
                "value",
                "today",
            ),
            show="headings",
            height=3,
        )

        self.brokerage_tree.tag_configure(
            "today_positive",
            foreground="green",
        )
        self.brokerage_tree.tag_configure(
            "today_negative",
            foreground="red",
        )
        self.brokerage_tree.tag_configure(
            "today_zero",
            foreground="black",
        )

        self.brokerage_tree.heading(
            "brokerage",
            text="Brokerage",
        )

        self.brokerage_tree.heading(
            "value",
            text="Current Market Value",
        )

        self.brokerage_tree.heading(
            "today",
            text="Today",
        )


        self.brokerage_tree.column(
            "brokerage",
            width=180,
            minwidth=150,
            stretch=False,
        )

        self.brokerage_tree.column(
            "value",
            width=220,
            minwidth=190,
            anchor="e",
            stretch=False,
        )

        self.brokerage_tree.column(
            "today",
            width=300,
            minwidth=260,
            anchor="e",
            stretch=True,
        )


        self.brokerage_tree.grid(
            row=0,
            column=0,
            sticky="ew",
        )

        brokerage_scrollbar = ttk.Scrollbar(
            brokerage_frame,
            orient="vertical",
            command=self.brokerage_tree.yview,
        )

        brokerage_scrollbar.grid(
            row=0,
            column=1,
            sticky="ns",
        )

        self.brokerage_tree.configure(
            yscrollcommand=brokerage_scrollbar.set,
        )

        # ---------------------------------------------------------
        # Accounts
        # ---------------------------------------------------------

        accounts_frame = ttk.LabelFrame(
            self,
            text="Accounts",
            padding=8,
        )

        accounts_frame.grid(
            row=5,
            column=0,
            sticky="nsew",
        )

        accounts_frame.columnconfigure(0, weight=1)
        accounts_frame.rowconfigure(0, weight=1)

        self.accounts_tree = ttk.Treeview(
            accounts_frame,
            columns=(
                "brokerage",
                "account",
                "name",
                "value",
                "today",
                "roi",
            ),
            show="headings",
            height=10,
        )

        self.accounts_tree.tag_configure(
            "today_positive",
            foreground="green",
        )
        self.accounts_tree.tag_configure(
            "today_negative",
            foreground="red",
        )
        self.accounts_tree.tag_configure(
            "today_zero",
            foreground="black",
        )

        self.accounts_tree.heading(
            "brokerage",
            text="Brokerage",
        )

        self.accounts_tree.heading(
            "account",
            text="Account",
        )

        self.accounts_tree.heading(
            "name",
            text="Name",
        )

        self.accounts_tree.heading(
            "value",
            text="Current Market Value",
        )

        self.accounts_tree.heading(
            "today",
            text="Today",
        )


        self.accounts_tree.heading(
            "roi",
            text="ROI",
        )

        # Keep the complete table visible in the normal window.

        self.accounts_tree.column(
            "brokerage",
            width=145,
            minwidth=130,
            stretch=False,
        )

        self.accounts_tree.column(
            "account",
            width=115,
            minwidth=105,
            stretch=False,
        )

        self.accounts_tree.column(
            "name",
            width=145,
            minwidth=120,
            stretch=True,
        )

        self.accounts_tree.column(
            "value",
            width=175,
            minwidth=165,
            anchor="e",
            stretch=False,
        )

        self.accounts_tree.column(
            "today",
            width=225,
            minwidth=210,
            anchor="e",
            stretch=True,
        )


        self.accounts_tree.column(
            "roi",
            width=85,
            minwidth=75,
            anchor="e",
            stretch=False,
        )

        self.accounts_tree.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        account_actions = ttk.Frame(accounts_frame)
        account_actions.grid(
            row=1,
            column=0,
            sticky="w",
            pady=(8, 0),
        )

        ttk.Button(
            account_actions,
            text="Change Account Name",
            command=self._change_account_name,
        ).pack(side="left")

        accounts_scrollbar = ttk.Scrollbar(
            accounts_frame,
            orient="vertical",
            command=self.accounts_tree.yview,
        )

        accounts_scrollbar.grid(
            row=0,
            column=1,
            sticky="ns",
        )

        self.accounts_tree.configure(
            yscrollcommand=accounts_scrollbar.set,
        )

        self.accounts_tree.bind(
            "<Double-1>",
            self._open_account_holdings,
        )

    # =============================================================
    # Update
    # =============================================================

    def _update_portfolio(self) -> None:
        """Update all account and consolidated portfolio values."""

        self.status_label.configure(text="Updating...")
        self.progress_bar.configure(value=0)
        self.progress_label.configure(
            text="Updating Portfolio: 0%   0 / 0   Starting..."
        )
        self.update_idletasks()

        try:
            initialize_database()

            session = get_session()

            try:
                service = PortfolioValuationService(
                    session,
                    progress_callback=self._update_progress,
                )

                total_value = service.update_all_accounts()

                # Capture the values calculated by the valuation
                # service while they are still available.
                tsx_change = getattr(
                    service,
                    "tsx_daily_change_percent",
                    None,
                )

            finally:
                session.close()

            self._load_current_values(
                tsx_change=tsx_change
            )

            self.progress_bar.configure(value=100)
            self.progress_label.configure(
                text=(
                    "Updating Portfolio: 100%   Complete   "
                    f"TOTAL: {self._format_currency(total_value)}"
                )
            )

            self.status_label.configure(
                text=(
                    f"Updated: "
                    f"{self._format_currency(total_value)}"
                )
            )

            # Notify the Accounts tab that the portfolio snapshots have
            # been updated.  Accounts listens for this event and reloads
            # its values automatically, so a manual Refresh is not needed.
            self.event_generate("<<PortfolioUpdated>>", when="tail")

        except Exception as exc:
            self.progress_label.configure(
                text=(
                    "Update failed: "
                    f"{type(exc).__name__}: {exc}"
                )
            )
            self.progress_bar.configure(value=0)

            self.status_label.configure(
                text="Update failed."
            )

            messagebox.showerror(
                "Portfolio Update Error",
                f"{type(exc).__name__}: {exc}",
            )

    def _update_progress(
        self,
        count: int,
        total: int,
        symbol: str,
    ) -> None:
        """Update the single-line portfolio progress display."""
        if total <= 0:
            percent = 0
        else:
            percent = min(100, int(count * 100 / total))

        self.progress_bar.configure(value=percent)
        self.progress_label.configure(
            text=(
                f"Updating Portfolio: {percent}%   "
                f"{count} / {total}   {symbol}"
            )
        )
        self.update_idletasks()

    # =============================================================
    # Load values
    # =============================================================

    def _load_current_values(
        self,
        tsx_change: Decimal | None = None,
    ) -> None:
        """Load today's saved portfolio values."""

        try:
            initialize_database()

            session = get_session()

            try:
                today = date.today()

                # -------------------------------------------------
                # Consolidated value
                # -------------------------------------------------

                consolidated = session.scalar(
                    select(PortfolioSnapshot)
                    .where(
                        PortfolioSnapshot.account_id.is_(None),
                        PortfolioSnapshot.snapshot_date == today,
                    )
                )

                if consolidated is None:
                    self.total_value_label.configure(
                        text="$0.00"
                    )

                    self.total_change_label.configure(
                        text="Today: --"
                    )

                else:
                    self.total_value_label.configure(
                        text=self._format_currency(
                            consolidated.total_value
                        )
                    )

                    total_change, total_percent = (
                        self._calculate_daily_change(
                            None,
                            session=session,
                        )
                    )

                    if total_change is None:
                        self.total_change_label.configure(
                            text="Today: --"
                        )
                    else:
                        self.total_change_label.configure(
                            text=(
                                "Today: "
                                f"{self._format_signed_currency(total_change)} "
                                f"({self._format_percent(total_percent)})"
                            )
                        )

                # -------------------------------------------------
                # TSX
                # -------------------------------------------------

                if tsx_change is not None:
                    self.tsx_label.configure(
                        text=(
                            "TSX: "
                            f"{self._format_percent(tsx_change)}"
                        )
                    )
                else:
                    self.tsx_label.configure(
                        text="TSX: --"
                    )

                # -------------------------------------------------
                # Account values
                # -------------------------------------------------

                rows = session.execute(
                    select(
                        Account,
                        Brokerage.name,
                        PortfolioSnapshot.total_value,
                    )
                    .join(
                        Brokerage,
                        Brokerage.id == Account.brokerage_id,
                    )
                    .join(
                        PortfolioSnapshot,
                        PortfolioSnapshot.account_id
                        == Account.id,
                    )
                    .where(
                        PortfolioSnapshot.snapshot_date == today,
                    )
                    .order_by(
                        Brokerage.name,
                        Account.account_number,
                    )
                ).all()

                self._display_accounts(
                    rows,
                    session,
                    tsx_change,
                )

                # -------------------------------------------------
                # Brokerage values
                # -------------------------------------------------

                self._display_brokerages(
                    session,
                    tsx_change,
                )

            finally:
                session.close()

        except Exception as exc:
            self.status_label.configure(
                text=(
                    f"Unable to load values: "
                    f"{type(exc).__name__}"
                )
            )

    # =============================================================
    # Display accounts
    # =============================================================

    def _display_accounts(
        self,
        rows,
        session,
        tsx_change: Decimal | None,
    ) -> None:
        """Display account values and performance."""

        for item in self.accounts_tree.get_children():
            self.accounts_tree.delete(item)

        for account, brokerage_name, value in rows:

            change, change_percent = (
                self._calculate_daily_change(
                    account.id,
                    session=session,
                )
            )

            roi = self._calculate_roi(
                account.id,
                value,
                session,
            )

            if change is None:
                today_text = "--"
            else:
                today_text = (
                    f"{self._format_signed_currency(change)} "
                    f"({self._format_percent(change_percent)})"
                )

            if change is None or change == 0:
                today_tag = "today_zero"
            elif change > 0:
                today_tag = "today_positive"
            else:
                today_tag = "today_negative"

            self.accounts_tree.insert(
                "",
                "end",
                iid=str(account.id),
                values=(
                    brokerage_name,
                    account.account_number,
                    account.name,
                    self._format_currency(value),
                    today_text,
                    self._format_percent(roi),
                ),
                tags=(today_tag,),
            )

    # =============================================================
    # Display brokerages
    # =============================================================

    def _display_brokerages(
        self,
        session,
        tsx_change: Decimal | None,
    ) -> None:
        """Display current values and live daily changes by brokerage."""

        for item in self.brokerage_tree.get_children():
            self.brokerage_tree.delete(item)

        today = date.today()

        rows = session.execute(
            select(
                Brokerage.id,
                Brokerage.name,
                func.sum(PortfolioSnapshot.total_value),
                func.sum(PortfolioSnapshot.daily_change),
            )
            .join(
                Account,
                Account.brokerage_id == Brokerage.id,
            )
            .join(
                PortfolioSnapshot,
                PortfolioSnapshot.account_id == Account.id,
            )
            .where(
                PortfolioSnapshot.snapshot_date == today,
            )
            .group_by(
                Brokerage.id,
                Brokerage.name,
            )
            .order_by(
                Brokerage.name,
            )
        ).all()

        for (
            brokerage_id,
            brokerage_name,
            value,
            change_value,
        ) in rows:
            value = Decimal(str(value or 0))

            if change_value is None:
                change = None
                change_percent = None
            else:
                change = Decimal(str(change_value))
                previous_value = value - change
                change_percent = (
                    change / previous_value * Decimal("100")
                    if previous_value != 0
                    else Decimal("0")
                )

            today_text = (
                "--"
                if change is None
                else (
                    f"{self._format_signed_currency(change)} "
                    f"({self._format_percent(change_percent)})"
                )
            )

            tsx_text = (
                "--"
                if tsx_change is None
                else self._format_percent(tsx_change)
            )

            self.brokerage_tree.insert(
                "",
                "end",
                values=(
                    brokerage_name,
                    self._format_currency(value),
                    today_text,
                    tsx_text,
                ),
            )

    # =============================================================
    # Account holdings
    # =============================================================

    def _open_account_holdings(self, event=None) -> None:
        """Open the holdings window for the selected account."""

        selected = self.accounts_tree.selection()

        if not selected:
            return

        account_id = int(selected[0])
        values = self.accounts_tree.item(selected[0], "values")

        account_number = str(values[1]) if len(values) > 1 else ""
        account_name = str(values[2]) if len(values) > 2 else ""

        session = None

        try:
            initialize_database()
            session = get_session()

            portfolio_service = PortfolioService(session)
            portfolio = portfolio_service.get_latest_portfolio(
                account_id
            )

            if portfolio is None:
                messagebox.showinfo(
                    "Account Holdings",
                    "No imported holdings were found for this account.",
                )
                return

            holdings_window = tk.Toplevel(self)
            holdings_window.title(
                f"Account Holdings - {account_number}"
            )
            holdings_window.geometry("1450x700")
            holdings_window.minsize(1100, 550)

            valuation_service = PortfolioValuationService(session)
            symbols = {"CAD=X"}
            symbols.update(holding.symbol for holding in portfolio.holdings)
            valuation_service._prepare_price_cache(symbols)

            (
                current_holdings,
                current_cash,
                current_total,
                current_daily_change,
            ) = valuation_service.calculate_current_values(portfolio)

            self._build_account_holdings_window(
                holdings_window,
                account_number,
                account_name,
                portfolio,
                current_holdings,
                current_cash,
                current_total,
                current_daily_change,
            )

        except Exception as exc:
            messagebox.showerror(
                "Account Holdings",
                f"Unable to load account holdings:\n\n"
                f"{type(exc).__name__}: {exc}",
            )
        finally:
            if session is not None:
                session.close()

    def _build_account_holdings_window(
        self,
        window: tk.Toplevel,
        account_number: str,
        account_name: str,
        portfolio,
        current_holdings,
        current_cash,
        current_total,
        current_daily_change,
    ) -> None:
        """Build the account holdings window."""

        window.columnconfigure(0, weight=1)
        window.rowconfigure(3, weight=1)

        header = ttk.Frame(window)
        header.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=15,
            pady=(15, 10),
        )

        ttk.Label(
            header,
            text=(
                f"Account {account_number}"
                + (f" - {account_name}" if account_name else "")
            ),
            font=("Segoe UI", 16, "bold"),
        ).pack(side="left")

        ttk.Label(
            header,
            text=(
                f"Snapshot: "
                f"{portfolio.snapshot_date.strftime('%Y-%m-%d')}"
            ),
            font=("Segoe UI", 10),
        ).pack(side="right")

        summary = ttk.LabelFrame(
            window,
            text="Account Summary",
            padding=10,
        )
        summary.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=15,
            pady=(0, 10),
        )

        current_by_symbol = {
            item.symbol: item for item in current_holdings
        }

        total_market_value = current_total

        # Cost basis is retained from the brokerage snapshot.  Calculating
        # it as market value minus brokerage unrealized gain also handles
        # option contract multipliers correctly.
        total_cost = sum(
            (
                holding.market_value
                - (holding.unrealized_gain or Decimal("0"))
                for holding in portfolio.holdings
            ),
            Decimal("0"),
        )

        total_unrealized_gain = total_market_value - total_cost
        total_gain_percent = (
            total_unrealized_gain / total_cost * Decimal("100")
            if total_cost != 0
            else Decimal("0")
        )

        total_daily_change = current_daily_change
        previous_close_value = total_market_value - total_daily_change
        total_daily_change_percent = (
            total_daily_change / previous_close_value * Decimal("100")
            if previous_close_value != 0
            else Decimal("0")
        )
        total_daily_change_text = (
            f"{self._format_signed_currency(total_daily_change)} "
            f"({self._format_percent(total_daily_change_percent)})"
        )

        total_cash_cad = sum(
            (item.current_cad_value for item in current_cash),
            Decimal("0"),
        )

        summary.columnconfigure(1, weight=1)
        summary.columnconfigure(3, weight=1)
        summary.columnconfigure(5, weight=1)
        summary.columnconfigure(7, weight=1)

        summary_items = (
            ("Market Value:", self._format_currency(total_market_value)),
            ("Cost:", self._format_currency(total_cost)),
            (
                "Unrealized Gain:",
                (
                    f"{self._format_signed_currency(total_unrealized_gain)} "
                    f"({self._format_percent(total_gain_percent)})"
                ),
            ),
            ("Today:", total_daily_change_text),
        )

        for column, (label, value) in enumerate(summary_items):
            base = column * 2

            ttk.Label(
                summary,
                text=label,
                font=("Segoe UI", 10, "bold"),
            ).grid(
                row=0,
                column=base,
                sticky="e",
                padx=(5, 5),
            )

            ttk.Label(
                summary,
                text=value,
                font=("Segoe UI", 11, "bold"),
            ).grid(
                row=0,
                column=base + 1,
                sticky="w",
                padx=(0, 20),
            )

        # -------------------------------------------------------------
        # Cash
        # -------------------------------------------------------------
        cash_frame = ttk.LabelFrame(
            window,
            text="Cash",
            padding=8,
        )
        cash_frame.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=15,
            pady=(0, 10),
        )
        cash_frame.columnconfigure(0, weight=1)

        cash_tree = ttk.Treeview(
            cash_frame,
            columns=("currency", "amount", "cad_value"),
            show="headings",
            height=max(1, len(current_cash)),
        )
        cash_tree.heading("currency", text="Currency")
        cash_tree.heading("amount", text="Amount")
        cash_tree.heading("cad_value", text="CAD Value")
        cash_tree.column("currency", width=120, anchor="center", stretch=False)
        cash_tree.column("amount", width=180, anchor="e", stretch=False)
        cash_tree.column("cad_value", width=180, anchor="e", stretch=False)
        cash_tree.grid(row=0, column=0, sticky="ew")

        for item in current_cash:
            cash_tree.insert(
                "",
                "end",
                values=(
                    item.currency,
                    self._format_currency(item.amount),
                    self._format_currency(item.current_cad_value),
                ),
            )

        ttk.Label(
            cash_frame,
            text=f"Total Cash (CAD): {self._format_currency(total_cash_cad)}",
            font=("Segoe UI", 10, "bold"),
        ).grid(row=1, column=0, sticky="e", pady=(6, 0))

        # -------------------------------------------------------------
        # Holdings
        # -------------------------------------------------------------
        frame = ttk.LabelFrame(
            window,
            text="Holdings",
            padding=8,
        )
        frame.grid(
            row=3,
            column=0,
            sticky="nsew",
            padx=15,
            pady=(0, 15),
        )

        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        tree = ttk.Treeview(
            frame,
            columns=(
                "symbol",
                "company",
                "quantity",
                "average_cost",
                "price",
                "market_value",
                "unrealized_gain",
                "unrealized_gain_percent",
                "daily_change",
                "daily_change_percent",
            ),
            show="headings",
        )

        headings = {
            "symbol": "Symbol",
            "company": "Company",
            "quantity": "Quantity",
            "average_cost": "Average Cost",
            "price": "Price",
            "market_value": "Market Value",
            "unrealized_gain": "Unrealized Gain",
            "unrealized_gain_percent": "Gain %",
            "daily_change": "Today",
            "daily_change_percent": "Today %",
        }

        for column, heading in headings.items():
            tree.heading(column, text=heading)

        tree.column("symbol", width=100, minwidth=80, stretch=False)
        tree.column("company", width=260, minwidth=180, stretch=True)
        tree.column(
            "quantity",
            width=120,
            minwidth=100,
            anchor="e",
            stretch=False,
        )
        tree.column(
            "average_cost",
            width=140,
            minwidth=120,
            anchor="e",
            stretch=False,
        )
        tree.column(
            "price",
            width=120,
            minwidth=100,
            anchor="e",
            stretch=False,
        )
        tree.column(
            "market_value",
            width=160,
            minwidth=140,
            anchor="e",
            stretch=False,
        )
        tree.column(
            "unrealized_gain",
            width=170,
            minwidth=150,
            anchor="e",
            stretch=False,
        )
        tree.column(
            "unrealized_gain_percent",
            width=100,
            minwidth=90,
            anchor="e",
            stretch=False,
        )

        tree.column(
            "daily_change",
            width=140,
            minwidth=120,
            anchor="e",
            stretch=False,
        )
        tree.column(
            "daily_change_percent",
            width=100,
            minwidth=90,
            anchor="e",
            stretch=False,
        )

        for holding in sorted(
            portfolio.holdings,
            key=lambda item: item.symbol,
        ):
            current = current_by_symbol.get(holding.symbol)
            current_price = (
                current.current_price if current is not None else holding.price
            )
            current_market_value = (
                current.current_market_value
                if current is not None
                else holding.market_value
            )

            # Keep the brokerage cost basis, but calculate current unrealized
            # gain from the live current market value.
            cost = holding.market_value - (
                holding.unrealized_gain or Decimal("0")
            )
            current_gain = current_market_value - cost
            current_gain_percent = (
                current_gain / cost * Decimal("100")
                if cost != 0
                else Decimal("0")
            )

            quantity_text = f"{holding.quantity:,.6f}".rstrip("0").rstrip(".")

            current_daily_change = (
                current.daily_change
                if current is not None
                else Decimal("0")
            )
            current_daily_change_percent = (
                current.daily_change_percent
                if current is not None
                else Decimal("0")
            )

            daily_change_text = self._format_signed_currency(
                current_daily_change
            )
            daily_change_percent_text = self._format_percent(
                current_daily_change_percent
            )

            if current_daily_change == 0:
                today_tag = "today_zero"
            elif current_daily_change > 0:
                today_tag = "today_positive"
            else:
                today_tag = "today_negative"

            tree.insert(
                "",
                "end",
                values=(
                    holding.symbol,
                    holding.company_name,
                    quantity_text,
                    self._format_currency(holding.average_cost),
                    self._format_currency(current_price),
                    self._format_currency(current_market_value),
                    self._format_signed_currency(current_gain),
                    self._format_percent(current_gain_percent),
                    daily_change_text,
                    daily_change_percent_text,
                ),
                tags=(today_tag,),
            )

        tree.tag_configure(
            "today_positive",
            foreground="green",
        )
        tree.tag_configure(
            "today_negative",
            foreground="red",
        )
        tree.tag_configure(
            "today_zero",
            foreground="black",
        )

        tree.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        scrollbar = ttk.Scrollbar(
            frame,
            orient="vertical",
            command=tree.yview,
        )
        scrollbar.grid(
            row=0,
            column=1,
            sticky="ns",
        )

        tree.configure(
            yscrollcommand=scrollbar.set,
        )

        close_frame = ttk.Frame(window)
        close_frame.grid(
            row=4,
            column=0,
            sticky="e",
            padx=15,
            pady=(0, 15),
        )

        ttk.Button(
            close_frame,
            text="Close",
            command=window.destroy,
        ).pack(side="right")

    # =============================================================
    # Account name
    # =============================================================

    def _change_account_name(self) -> None:
        """Change and persist the friendly name of the selected account."""
        selected = self.accounts_tree.selection()

        if not selected:
            messagebox.showinfo(
                "Change Account Name",
                "Select an account first.",
            )
            return

        account_id = int(selected[0])
        values = self.accounts_tree.item(selected[0], "values")

        if len(values) < 3:
            return

        account_number = str(values[1])
        current_name = str(values[2])

        new_name = simpledialog.askstring(
            "Change Account Name",
            f"Account {account_number}:",
            initialvalue=current_name,
            parent=self,
        )

        if new_name is None:
            return

        new_name = new_name.strip()

        if not new_name:
            messagebox.showwarning(
                "Change Account Name",
                "The account name cannot be blank.",
            )
            return

        session = None

        try:
            initialize_database()
            session = get_session()

            account = session.scalar(
                select(Account).where(Account.id == account_id)
            )

            if account is None:
                raise ValueError(
                    f"Account ID {account_id} was not found."
                )

            account.name = new_name
            session.commit()

            updated_values = list(values)
            updated_values[2] = new_name

            self.accounts_tree.item(
                selected[0],
                values=updated_values,
            )

        except Exception as exc:
            if session is not None:
                session.rollback()

            messagebox.showerror(
                "Change Account Name",
                f"Unable to save account name:\n\n"
                f"{type(exc).__name__}: {exc}",
            )

        finally:
            if session is not None:
                session.close()

    # =============================================================
    # Daily change
    # =============================================================

    def _calculate_daily_change(
        self,
        account_id: int | None,
        session=None,
    ) -> tuple[Decimal | None, Decimal | None]:
        """Return the live daily change saved by PortfolioValuationService."""

        own_session = False

        if session is None:
            initialize_database()
            session = get_session()
            own_session = True

        try:
            today = date.today()

            current = session.scalar(
                select(PortfolioSnapshot)
                .where(
                    PortfolioSnapshot.account_id == account_id,
                    PortfolioSnapshot.snapshot_date == today,
                )
            )

            if current is None:
                return None, None

            if current.daily_change is not None:
                change = Decimal(str(current.daily_change))
                percent = (
                    Decimal(str(current.daily_change_percent))
                    if current.daily_change_percent is not None
                    else (
                        change
                        / (Decimal(str(current.total_value)) - change)
                        * Decimal("100")
                        if Decimal(str(current.total_value)) - change != 0
                        else Decimal("0")
                    )
                )
                return change, percent

            # Backward-compatible fallback for snapshots created before
            # daily_change fields were populated.
            previous = session.scalar(
                select(PortfolioSnapshot)
                .where(
                    PortfolioSnapshot.account_id == account_id,
                    PortfolioSnapshot.snapshot_date < today,
                )
                .order_by(PortfolioSnapshot.snapshot_date.desc())
                .limit(1)
            )

            if previous is None:
                return None, None

            current_value = Decimal(str(current.total_value))
            previous_value = Decimal(str(previous.total_value))
            change = current_value - previous_value

            percent = (
                change / previous_value * Decimal("100")
                if previous_value != 0
                else Decimal("0")
            )

            return change, percent

        finally:
            if own_session:
                session.close()


    # =============================================================
    # ROI
    # =============================================================

    def _calculate_roi(
        self,
        account_id: int,
        current_value: Decimal,
        session,
    ) -> Decimal:
        """
        Calculate account ROI.

        ROI = (ending value - starting value)
              / starting value
        """

        first_snapshot = session.scalar(
            select(PortfolioSnapshot)
            .where(
                PortfolioSnapshot.account_id
                == account_id,
            )
            .order_by(
                PortfolioSnapshot.snapshot_date.asc()
            )
            .limit(1)
        )

        if first_snapshot is None:
            return Decimal("0")

        starting_value = Decimal(
            str(first_snapshot.total_value)
        )

        if starting_value == 0:
            return Decimal("0")

        current_value = Decimal(
            str(current_value)
        )

        return (
            (
                current_value
                - starting_value
            )
            / starting_value
            * Decimal("100")
        )

    # =============================================================
    # Progress
    # =============================================================

    def _write_progress(self, message: str) -> None:
        """Display a final/status message on the single progress line."""
        self.progress_label.configure(text=message)
        self.update_idletasks()

    # =============================================================
    # Formatting
    # =============================================================

    @staticmethod
    def _format_currency(
        value: Decimal,
    ) -> str:
        """Format a Decimal as Canadian currency."""

        return (
            f"${Decimal(str(value)):,.2f}"
        )

    @staticmethod
    def _format_signed_currency(
        value: Decimal,
    ) -> str:
        """Format a signed currency value."""

        value = Decimal(str(value))

        if value >= 0:
            return f"+${value:,.2f}"

        return f"-${abs(value):,.2f}"

    @staticmethod
    def _format_percent(
        value: Decimal | None,
    ) -> str:
        """Format a percentage."""

        if value is None:
            return "--"

        value = Decimal(str(value))

        return f"{value:+.2f}%"

    # =============================================================
    # Standalone entry point
    # =============================================================


def main() -> None:
    """Run the portfolio tab standalone."""

    root = tk.Tk()
    root.title("Financial Model - Portfolio")
    root.geometry("1550x900")
    root.minsize(1200, 700)

    PortfolioTab(root).pack(
        fill="both",
        expand=True,
        padx=15,
        pady=15,
    )

    root.mainloop()


if __name__ == "__main__":
    main()