"""
Portfolio tab for the Financial Model GUI.
"""

import tkinter as tk
from datetime import date
from decimal import Decimal
from tkinter import font as tkfont
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

        self._today_cell_labels: dict[tk.Misc, dict[str, tk.Label]] = {}
        self._today_cell_data: dict[tk.Misc, dict[str, tuple[str, str]]] = {}

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
            width=190,
            minwidth=170,
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
            yscrollcommand=lambda *args: self._tree_scroll(
                self.brokerage_tree, brokerage_scrollbar, args
            ),
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
            width=105,
            minwidth=90,
            stretch=False,
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
            width=185,
            minwidth=165,
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

        self.accounts_tree.configure(
            yscrollcommand=lambda *args: self._tree_scroll(
                self.accounts_tree, accounts_scrollbar, args
            ),
        )

        self.accounts_tree.bind(
            "<Double-1>",
            self._open_account_holdings,
        )
        self.accounts_tree.bind(
            "<<TreeviewSelect>>",
            lambda _event: self._position_today_cells(
                self.accounts_tree, "today"
            ),
        )
        self.brokerage_tree.bind(
            "<<TreeviewSelect>>",
            lambda _event: self._position_today_cells(
                self.brokerage_tree, "today"
            ),
        )
        self.accounts_tree.bind(
            "<Configure>",
            lambda _event: self._position_today_cells(
                self.accounts_tree, "today"
            ),
        )
        self.brokerage_tree.bind(
            "<Configure>",
            lambda _event: self._position_today_cells(
                self.brokerage_tree, "today"
            ),
        )

    # =============================================================
    # Today cell colours
    # =============================================================

    @staticmethod
    def _change_color(change: Decimal | None) -> str:
        """Return the colour for a daily change."""
        if change is None or Decimal(str(change)) == 0:
            return "black"
        return "green" if Decimal(str(change)) > 0 else "red"

    def _tree_scroll(self, tree, scrollbar, args) -> None:
        """Update a scrollbar and reposition cell overlays after scrolling."""
        scrollbar.set(*args)
        self.after_idle(lambda: self._position_today_cells(tree))

    def _set_today_cell_data(
        self,
        tree,
        iid: str,
        column: str,
        text: str,
        foreground: str,
    ) -> None:
        """Store display data for a single coloured Treeview cell."""
        data = self._today_cell_data.setdefault(tree, {})
        data[f"{iid}:{column}"] = (text, foreground)

    def _position_today_cells(self, tree, column: str | None = None) -> None:
        """Draw coloured labels over the Today cells of a Treeview."""
        if not tree.winfo_exists():
            return

        data = self._today_cell_data.get(tree, {})
        labels = self._today_cell_labels.setdefault(tree, {})

        columns = [column] if column else [
            "today",
            "today_percent",
        ]

        tree_bg = ttk.Style().lookup("Treeview", "fieldbackground") or "white"
        selected_bg = ttk.Style().lookup(
            "Treeview", "selectbackground"
        ) or "#4a6984"
        selected_fg = ttk.Style().lookup(
            "Treeview", "selectforeground"
        ) or "white"

        for key, label in list(labels.items()):
            if not any(key.endswith(f":{col}") for col in columns):
                continue
            label.place_forget()

        for iid in tree.get_children():
            for col in columns:
                key = f"{iid}:{col}"
                if key not in data:
                    continue

                bbox = tree.bbox(iid, col)
                if not bbox:
                    continue

                x, y, width, height = bbox
                text, foreground = data[key]
                selected = iid in tree.selection()

                label = labels.get(key)
                if label is None or not label.winfo_exists():
                    label = tk.Label(
                        tree,
                        text=text,
                        anchor="e",
                        padx=4,
                        bd=0,
                        relief="flat",
                        font=tkfont.nametofont("TkDefaultFont"),
                    )
                    label.bind(
                        "<Button-1>",
                        lambda event, item=iid, tv=tree: self._select_tree_item(
                            tv, item
                        ),
                    )
                    labels[key] = label

                label.configure(
                    text=text,
                    fg=foreground,
                    bg=selected_bg if selected else tree_bg,
                )
                if selected:
                    label.configure(fg=foreground)
                label.place(
                    x=x,
                    y=y,
                    width=width,
                    height=height,
                )

    def _select_tree_item(self, tree, iid: str) -> None:
        """Select a Treeview item when its Today overlay is clicked."""
        tree.selection_set(iid)
        tree.focus(iid)
        self._position_today_cells(tree)

    def _destroy_today_cell_labels(self, tree) -> None:
        """Clean up Today cell overlays when a Treeview is destroyed."""
        labels = self._today_cell_labels.pop(tree, {})
        for label in labels.values():
            if label.winfo_exists():
                label.destroy()
        self._today_cell_data.pop(tree, None)

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
                            ),
                            foreground=self._change_color(total_change),
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

            if tsx_change is None:
                tsx_text = "--"
            else:
                tsx_text = self._format_percent(
                    tsx_change
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
                    self._format_percent(roi),
                ),
            )

            self._set_today_cell_data(
                self.accounts_tree,
                str(account.id),
                "today",
                today_text,
                self._change_color(change),
            )

        self.after_idle(
            lambda: self._position_today_cells(self.accounts_tree, "today")
        )

    # =============================================================
    # Display brokerages
    # =============================================================

    def _display_brokerages(
        self,
        session,
        tsx_change: Decimal | None,
    ) -> None:
        """Display consolidated live Yahoo values by brokerage."""
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
            .join(Account, Account.brokerage_id == Brokerage.id)
            .join(
                PortfolioSnapshot,
                PortfolioSnapshot.account_id == Account.id,
            )
            .where(PortfolioSnapshot.snapshot_date == today)
            .group_by(Brokerage.id, Brokerage.name)
            .order_by(Brokerage.name)
        ).all()

        for _brokerage_id, brokerage_name, value, change in rows:
            value = Decimal(str(value or 0))
            change = Decimal(str(change or 0))
            percent = self._daily_change_percent(value, change)

            today_text = (
                f"{self._format_signed_currency(change)} "
                f"({self._format_percent(percent)})"
            )

            iid = self.brokerage_tree.insert(
                "",
                "end",
                values=(
                    brokerage_name,
                    self._format_currency(value),
                    today_text,
                ),
            )

            self._set_today_cell_data(
                self.brokerage_tree,
                iid,
                "today",
                today_text,
                self._change_color(change),
            )

        self.after_idle(
            lambda: self._position_today_cells(self.brokerage_tree, "today")
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

            account_snapshot = session.scalar(
                select(PortfolioSnapshot).where(
                    PortfolioSnapshot.account_id == account_id,
                    PortfolioSnapshot.snapshot_date == date.today(),
                )
            )

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
                account_snapshot,
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
        account_snapshot: PortfolioSnapshot | None,
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

        # The account's market value must be the exact same value shown
        # on the main Portfolio screen.  PortfolioSnapshot.total_value
        # includes both securities and cash, whereas summing holdings alone
        # excludes cash.
        if account_snapshot is not None:
            total_market_value = Decimal(
                str(account_snapshot.total_value)
            )
        else:
            total_market_value = sum(
                (
                    holding.current_market_value
                    if holding.current_market_value is not None
                    else holding.market_value
                    for holding in portfolio.holdings
                ),
                Decimal("0"),
            )

        total_cost = sum(
            (
                holding.average_cost * holding.quantity
                for holding in portfolio.holdings
            ),
            Decimal("0"),
        )

        total_unrealized_gain = sum(
            (
                holding.unrealized_gain
                for holding in portfolio.holdings
            ),
            Decimal("0"),
        )

        total_gain_percent = (
            total_unrealized_gain / total_cost * Decimal("100")
            if total_cost != 0
            else Decimal("0")
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
            (
                "Today:",
                (
                    self._format_signed_currency(
                        Decimal(str(account_snapshot.daily_change))
                    )
                    if account_snapshot is not None
                    and account_snapshot.daily_change is not None
                    else self._format_signed_currency(
                        sum(
                            (
                                holding.current_daily_change
                                or Decimal("0")
                                for holding in portfolio.holdings
                            ),
                            Decimal("0"),
                        )
                    )
                ),
            ),
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

            value_label = ttk.Label(
                summary,
                text=value,
                font=("Segoe UI", 11, "bold"),
            )
            if label == "Today:":
                today_change = (
                    Decimal(str(account_snapshot.daily_change))
                    if account_snapshot is not None
                    and account_snapshot.daily_change is not None
                    else sum(
                        (
                            holding.current_daily_change
                            or Decimal("0")
                            for holding in portfolio.holdings
                        ),
                        Decimal("0"),
                    )
                )
                value_label.configure(
                    foreground=self._change_color(today_change)
                )
            value_label.grid(
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
                "today",
                "today_percent",
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
            "today": "Today",
            "today_percent": "Today %",
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
            "today",
            width=145,
            minwidth=125,
            anchor="e",
            stretch=False,
        )
        tree.column(
            "today_percent",
            width=90,
            minwidth=80,
            anchor="e",
            stretch=False,
        )

        for holding in sorted(
            portfolio.holdings,
            key=lambda item: item.symbol,
        ):
            cost = holding.average_cost * holding.quantity

            gain_percent = (
                holding.unrealized_gain / cost * Decimal("100")
                if cost != 0
                else Decimal("0")
            )

            quantity_text = f"{holding.quantity:,.6f}".rstrip("0").rstrip(".")

            today_value = (
                self._format_signed_currency(
                    holding.current_daily_change
                )
                if holding.current_daily_change is not None
                else "--"
            )
            today_percent_value = (
                self._format_percent(
                    holding.current_daily_change_percent
                )
                if holding.current_daily_change_percent is not None
                else "--"
            )

            iid = tree.insert(
                "",
                "end",
                values=(
                    holding.symbol,
                    holding.company_name,
                    quantity_text,
                    self._format_currency(holding.average_cost),
                    self._format_currency(
                        holding.current_price
                        if holding.current_price is not None
                        else holding.price
                    ),
                    self._format_currency(
                        holding.current_market_value
                        if holding.current_market_value is not None
                        else holding.market_value
                    ),
                    self._format_signed_currency(
                        holding.unrealized_gain
                    ),
                    self._format_percent(gain_percent),
                    today_value,
                    today_percent_value,
                ),
            )

            self._set_today_cell_data(
                tree,
                iid,
                "today",
                today_value,
                self._change_color(holding.current_daily_change),
            )
            self._set_today_cell_data(
                tree,
                iid,
                "today_percent",
                today_percent_value,
                self._change_color(holding.current_daily_change),
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
            yscrollcommand=lambda *args: self._tree_scroll(
                tree, scrollbar, args
            ),
        )

        tree.bind(
            "<Configure>",
            lambda _event: self._position_today_cells(tree),
        )
        tree.bind(
            "<<TreeviewSelect>>",
            lambda _event: self._position_today_cells(tree),
        )

        tree.bind(
            "<Destroy>",
            lambda _event: self._destroy_today_cell_labels(tree),
        )

        self.after_idle(
            lambda: self._position_today_cells(tree)
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
        """Return live Yahoo daily change saved by Update Portfolio."""
        own_session = False
        if session is None:
            initialize_database()
            session = get_session()
            own_session = True

        try:
            snapshot = session.scalar(
                select(PortfolioSnapshot).where(
                    PortfolioSnapshot.account_id == account_id,
                    PortfolioSnapshot.snapshot_date == date.today(),
                )
            )
            if snapshot is None or snapshot.daily_change is None:
                return None, None
            change = Decimal(str(snapshot.daily_change))
            percent = (
                Decimal(str(snapshot.daily_change_percent))
                if snapshot.daily_change_percent is not None
                else self._daily_change_percent(snapshot.total_value, change)
            )
            return change, percent
        finally:
            if own_session:
                session.close()

    @staticmethod
    def _daily_change_percent(
        current_value: Decimal,
        daily_change: Decimal,
    ) -> Decimal:
        """Calculate today's percentage from the live Yahoo snapshot."""
        previous_close = Decimal(str(current_value)) - Decimal(str(daily_change))
        if previous_close == 0:
            return Decimal("0")
        return Decimal(str(daily_change)) / previous_close * Decimal("100")

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