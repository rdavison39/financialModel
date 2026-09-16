"""
Portfolio tab for the Financial Model GUI.
"""

import tkinter as tk
from datetime import date, timedelta
from decimal import Decimal
from tkinter import messagebox, simpledialog, ttk

from sqlalchemy import select, func

from src.database import get_session
from src.database_init import initialize_database
from src.models.account import Account
from src.models.brokerage import Brokerage
from src.models.portfolio_snapshot import PortfolioSnapshot
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
                "tsx",
            ),
            show="headings",
            height=3,
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

        self.brokerage_tree.heading(
            "tsx",
            text="TSX",
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

        self.brokerage_tree.column(
            "tsx",
            width=100,
            minwidth=90,
            anchor="e",
            stretch=False,
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
                "tsx",
                "roi",
            ),
            show="headings",
            height=10,
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
            "tsx",
            text="TSX",
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
            width=255,
            minwidth=240,
            anchor="e",
            stretch=False,
        )

        self.accounts_tree.column(
            "tsx",
            width=85,
            minwidth=75,
            anchor="e",
            stretch=False,
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

        def accounts_scroll(*args):
            accounts_scrollbar.set(*args)
            self._refresh_today_cell_colors()

        self.accounts_tree.configure(
            yscrollcommand=accounts_scroll,
        )

        self.accounts_tree.bind(
            "<Double-1>",
            self._open_account_holdings,
        )

        self.accounts_tree.bind(
            "<Configure>",
            lambda event: self._refresh_today_cell_colors(),
            add="+",
        )
        self.accounts_tree.bind(
            "<MouseWheel>",
            lambda event: self.accounts_tree.after_idle(
                self._refresh_today_cell_colors
            ),
            add="+",
        )
        self.accounts_tree.bind(
            "<<TreeviewSelect>>",
            lambda event: self.accounts_tree.after_idle(
                self._refresh_today_cell_colors
            ),
            add="+",
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
                self._calculate_imported_daily_change(
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

            tsx_text = (
                "--"
                if tsx_change is None
                else self._format_percent(tsx_change)
            )

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
                    tsx_text,
                    self._format_percent(roi),
                ),
            )

        self._refresh_today_cell_colors()

    def _calculate_imported_daily_change(
        self,
        account_id: int,
        session=None,
    ) -> tuple[Decimal | None, Decimal | None]:
        """Calculate today's change from imported brokerage values."""

        own_session = False

        if session is None:
            initialize_database()
            session = get_session()
            own_session = True

        try:
            portfolio = PortfolioService(session).get_latest_portfolio(
                account_id
            )

            if portfolio is None:
                return None, None

            total_change = Decimal("0")
            previous_close_value = Decimal("0")
            has_daily_data = False

            for holding in portfolio.holdings:
                if holding.daily_change is None:
                    continue

                has_daily_data = True
                quantity = Decimal(str(holding.quantity or 0))
                change = quantity * Decimal(str(holding.daily_change))

                if holding.currency == "USD":
                    # The brokerage percentage is still useful for the
                    # account calculation when the previous-close field
                    # is unavailable.
                    if holding.daily_change_percent is not None:
                        pct = Decimal(
                            str(holding.daily_change_percent)
                        )
                        if pct != 0:
                            previous_close_value += (
                                change / pct * Decimal("100")
                            )
                elif holding.previous_close is not None:
                    previous_close_value += (
                        quantity
                        * Decimal(str(holding.previous_close))
                    )

                total_change += change

            if not has_daily_data:
                return None, None

            if previous_close_value != 0:
                percent = (
                    total_change
                    / previous_close_value
                    * Decimal("100")
                )
            else:
                percent = Decimal("0")

            return total_change, percent

        finally:
            if own_session:
                session.close()

    def _refresh_today_cell_colors(self) -> None:
        """Color only the Today column without disturbing other cells."""
        if not hasattr(self, "_today_cell_labels"):
            self._today_cell_labels = {}

        for label in self._today_cell_labels.values():
            label.destroy()

        self._today_cell_labels.clear()

        style = ttk.Style(self)
        normal_background = style.lookup(
            "Treeview", "background"
        ) or "white"
        selected_background = style.lookup(
            "Treeview",
            "background",
            ("selected",),
        ) or "#4a6984"

        # Treeview does not support foreground colour on an individual
        # cell.  Put a small label INSIDE the Treeview instead.  This is
        # important: using accounts_tree.master makes the label escape
        # the table and causes the overlap seen previously.
        today_column_index = "#5"

        for item_id in self.accounts_tree.get_children():
            bbox = self.accounts_tree.bbox(
                item_id,
                today_column_index,
            )

            if not bbox:
                continue

            x, y, width, height = bbox
            values = self.accounts_tree.item(item_id, "values")

            if len(values) < 5:
                continue

            text = str(values[4])

            if text.startswith("+"):
                foreground = "green"
            elif text.startswith("-"):
                foreground = "red"
            else:
                foreground = "black"

            selected = item_id in self.accounts_tree.selection()

            label = tk.Label(
                self.accounts_tree,
                text=text,
                font=("Segoe UI", 9),
                foreground=foreground,
                background=(
                    selected_background
                    if selected
                    else normal_background
                ),
                anchor="e",
                padx=4,
                bd=0,
                highlightthickness=0,
            )

            label.place(
                x=x,
                y=y,
                width=width,
                height=height,
            )
            label.lift()

            def select_account(event, item_id=item_id):
                self.accounts_tree.selection_set(item_id)
                self.accounts_tree.focus(item_id)
                self.accounts_tree.after_idle(
                    self._refresh_today_cell_colors
                )

            def open_account(event, item_id=item_id):
                self.accounts_tree.selection_set(item_id)
                self.accounts_tree.focus(item_id)
                self._open_account_holdings(event)

            label.bind("<Button-1>", select_account)
            label.bind("<Double-1>", open_account)

            self._today_cell_labels[item_id] = label


    # =============================================================
    # Display brokerages
    # =============================================================

    def _display_brokerages(
        self,
        session,
        tsx_change: Decimal | None,
    ) -> None:
        """Display consolidated values by brokerage."""

        for item in self.brokerage_tree.get_children():
            self.brokerage_tree.delete(item)

        today = date.today()

        rows = session.execute(
            select(
                Brokerage.id,
                Brokerage.name,
                func.sum(PortfolioSnapshot.total_value),
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

        for brokerage_id, brokerage_name, value in rows:

            previous_value = session.scalar(
                select(
                    func.sum(
                        PortfolioSnapshot.total_value
                    )
                )
                .join(
                    Account,
                    Account.id
                    == PortfolioSnapshot.account_id,
                )
                .where(
                    Account.brokerage_id
                    == brokerage_id,
                    PortfolioSnapshot.snapshot_date
                    < today,
                )
                .order_by(
                    PortfolioSnapshot.snapshot_date.desc()
                )
            )

            if previous_value is None:
                change = None
                change_percent = None
            else:
                current_value = Decimal(
                    str(value or 0)
                )

                previous_value = Decimal(
                    str(previous_value)
                )

                change = (
                    current_value
                    - previous_value
                )

                if previous_value != 0:
                    change_percent = (
                        change
                        / previous_value
                        * Decimal("100")
                    )
                else:
                    change_percent = Decimal("0")

            if change is None:
                today_text = "--"
            else:
                today_text = (
                    f"{self._format_signed_currency(change)} "
                    f"({self._format_percent(change_percent)})"
                )

            if tsx_change is None:
                tsx_text = "--"
            else:
                tsx_text = self._format_percent(
                    tsx_change
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

            portfolio = PortfolioService(session).get_latest_portfolio(
                account_id
            )

            if portfolio is None:
                messagebox.showinfo(
                    "Account Holdings",
                    "No imported holdings were found for this account.",
                )
                return

            today = date.today()

            current_snapshot = session.scalar(
                select(PortfolioSnapshot)
                .where(
                    PortfolioSnapshot.account_id == account_id,
                    PortfolioSnapshot.snapshot_date == today,
                )
            )

            if current_snapshot is None:
                messagebox.showinfo(
                    "Account Holdings",
                    "This account has not been updated today. "
                    "Click 'Update Portfolio' first.",
                )
                return

            holdings_window = tk.Toplevel(self)
            holdings_window.title(
                f"Account Holdings - {account_number}"
            )
            holdings_window.geometry("1450x700")
            holdings_window.minsize(1100, 550)

            self._build_account_holdings_window(
                holdings_window,
                account_number,
                account_name,
                portfolio,
                live_total_value=Decimal(
                    str(current_snapshot.total_value or 0)
                ),
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
        live_total_value: Decimal | None = None,
    ) -> None:
        """Build the account holdings window."""

        window.columnconfigure(0, weight=1)
        window.rowconfigure(2, weight=1)

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
            text="Current valuation",
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

        total_market_value = (
            Decimal(str(live_total_value))
            if live_total_value is not None
            else sum(
                (
                    Decimal(str(h.market_value or 0))
                    for h in portfolio.holdings
                ),
                Decimal("0"),
            )
        )

        holdings_with_cost = [
            h for h in portfolio.holdings
            if h.average_cost is not None
        ]
        holdings_with_gain = [
            h for h in portfolio.holdings
            if h.unrealized_gain is not None
        ]

        total_cost = sum(
            (
                Decimal(str(h.average_cost))
                * Decimal(str(h.quantity or 0))
                for h in holdings_with_cost
            ),
            Decimal("0"),
        )

        total_unrealized_gain = sum(
            (
                Decimal(str(h.unrealized_gain))
                for h in holdings_with_gain
            ),
            Decimal("0"),
        )

        total_daily_change = sum(
            (
                Decimal(str(h.daily_change or 0))
                * Decimal(str(h.quantity or 0))
                for h in portfolio.holdings
                if h.daily_change is not None
            ),
            Decimal("0"),
        )

        previous_close_value = sum(
            (
                Decimal(str(h.previous_close or 0))
                * Decimal(str(h.quantity or 0))
                for h in portfolio.holdings
                if h.previous_close is not None
                and h.previous_close != 0
            ),
            Decimal("0"),
        )

        total_gain_percent = (
            total_unrealized_gain / total_cost * Decimal("100")
            if total_cost != 0
            else None
        )

        total_daily_change_percent = (
            total_daily_change
            / previous_close_value
            * Decimal("100")
            if previous_close_value != 0
            else Decimal("0")
        )

        summary.columnconfigure(1, weight=1)
        summary.columnconfigure(3, weight=1)
        summary.columnconfigure(5, weight=1)
        summary.columnconfigure(7, weight=1)

        cost_text = (
            self._format_currency(total_cost)
            if holdings_with_cost
            else "--"
        )
        gain_text = (
            f"{self._format_signed_currency(total_unrealized_gain)} "
            f"({self._format_percent(total_gain_percent)})"
            if holdings_with_gain
            else "--"
        )
        daily_text = (
            f"{self._format_signed_currency(total_daily_change)} "
            f"({self._format_percent(total_daily_change_percent)})"
            if any(h.daily_change is not None for h in portfolio.holdings)
            else "--"
        )

        summary_items = (
            ("Market Value:", self._format_currency(total_market_value)),
            ("Cost:", cost_text),
            ("Unrealized Gain:", gain_text),
            ("Today:", daily_text),
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

        frame = ttk.LabelFrame(
            window,
            text="Holdings",
            padding=8,
        )
        frame.grid(
            row=2,
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
            "daily_change": "Daily Change",
            "daily_change_percent": "Daily %",
        }

        for column, heading in headings.items():
            tree.heading(column, text=heading)

        widths = {
            "symbol": 100,
            "company": 260,
            "quantity": 120,
            "average_cost": 140,
            "price": 120,
            "market_value": 160,
            "unrealized_gain": 170,
            "unrealized_gain_percent": 100,
            "daily_change": 140,
            "daily_change_percent": 100,
        }

        for column, width in widths.items():
            tree.column(
                column,
                width=width,
                minwidth=max(80, width - 20),
                anchor="e" if column not in {"symbol", "company"} else "w",
                stretch=column == "company",
            )

        for holding in sorted(
            portfolio.holdings,
            key=lambda item: item.symbol,
        ):
            quantity = Decimal(str(holding.quantity or 0))

            quantity_text = (
                f"{quantity:,.6f}"
                .rstrip("0")
                .rstrip(".")
            )

            average_cost_text = (
                "--"
                if holding.average_cost is None
                else self._format_currency(holding.average_cost)
            )

            gain_text = (
                "--"
                if holding.unrealized_gain is None
                else self._format_signed_currency(
                    holding.unrealized_gain
                )
            )

            gain_percent_text = (
                "--"
                if holding.unrealized_gain_percent is None
                else self._format_percent(
                    holding.unrealized_gain_percent
                )
            )

            daily_change_text = (
                "--"
                if holding.daily_change is None
                else self._format_signed_currency(
                    Decimal(str(holding.daily_change)) * quantity
                )
            )

            daily_percent_text = (
                "--"
                if holding.daily_change_percent is None
                else self._format_percent(
                    holding.daily_change_percent
                )
            )

            tree.insert(
                "",
                "end",
                values=(
                    holding.symbol,
                    holding.company_name,
                    quantity_text,
                    average_cost_text,
                    self._format_currency(holding.price),
                    self._format_currency(holding.market_value),
                    gain_text,
                    gain_percent_text,
                    daily_change_text,
                    daily_percent_text,
                ),
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
            row=3,
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
        """
        Calculate today's change against the previous valuation.

        account_id=None means consolidated portfolio.
        """

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
                    PortfolioSnapshot.account_id
                    == account_id,
                    PortfolioSnapshot.snapshot_date
                    == today,
                )
            )

            if current is None:
                return None, None

            previous = session.scalar(
                select(PortfolioSnapshot)
                .where(
                    PortfolioSnapshot.account_id
                    == account_id,
                    PortfolioSnapshot.snapshot_date
                    < today,
                )
                .order_by(
                    PortfolioSnapshot.snapshot_date.desc()
                )
                .limit(1)
            )

            if previous is None:
                return None, None

            current_value = Decimal(
                str(current.total_value)
            )

            previous_value = Decimal(
                str(previous.total_value)
            )

            change = (
                current_value
                - previous_value
            )

            if previous_value == 0:
                percent = Decimal("0")
            else:
                percent = (
                    change
                    / previous_value
                    * Decimal("100")
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