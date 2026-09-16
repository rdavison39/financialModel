"""
Accounts tab for the Financial Model GUI.
"""

import tkinter as tk
from decimal import Decimal
from tkinter import messagebox, simpledialog, ttk

from sqlalchemy import select

from src.models.import_record import ImportRecord

from src.database import get_session
from src.database_init import initialize_database
from src.services.account_service import AccountService


class AccountsTab(ttk.Frame):
    """Display and manage investment accounts."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        self._build_ui()
        self.after(100, self._load_accounts)

    def _build_ui(self) -> None:
        """Build the Accounts page."""

        ttk.Label(
            self,
            text="Accounts",
            font=("Segoe UI", 18, "bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 15),
        )

        controls = ttk.Frame(self)
        controls.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(0, 6),
        )

        ttk.Button(
            controls,
            text="Refresh",
            command=self._load_accounts,
        ).pack(side="left")

        ttk.Button(
            controls,
            text="Rename Account",
            command=self._rename_account,
        ).pack(
            side="left",
            padx=(8, 0),
        )

        ttk.Button(
            controls,
            text="View Holdings",
            command=self._view_holdings,
        ).pack(
            side="left",
            padx=(8, 0),
        )

        compare = ttk.Frame(self)
        compare.grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(0, 10),
        )

        ttk.Label(
            compare,
            text="Compare Snapshots:",
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left")

        ttk.Label(compare, text="From:").pack(
            side="left",
            padx=(15, 4),
        )

        self.from_var = tk.StringVar()
        self.from_entry = ttk.Entry(
            compare,
            textvariable=self.from_var,
            width=12,
        )
        self.from_entry.pack(side="left")

        ttk.Label(compare, text="To:").pack(
            side="left",
            padx=(12, 4),
        )

        self.to_var = tk.StringVar()
        self.to_entry = ttk.Entry(
            compare,
            textvariable=self.to_var,
            width=12,
        )
        self.to_entry.pack(side="left")

        ttk.Button(
            compare,
            text="Compare",
            command=self._compare_snapshots,
        ).pack(
            side="left",
            padx=(10, 0),
        )

        ttk.Label(
            compare,
            text="YYYY-MM-DD",
        ).pack(
            side="left",
            padx=(8, 0),
        )

        frame = ttk.Frame(self)
        frame.grid(
            row=3,
            column=0,
            sticky="nsew",
        )
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        columns = (
            "brokerage",
            "account_number",
            "name",
            "current_value",
            "cash",
            "holdings",
            "last_import",
        )

        self.accounts_tree = ttk.Treeview(
            frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        headings = {
            "brokerage": "Brokerage",
            "account_number": "Account Number",
            "name": "Name",
            "current_value": "Current Value",
            "cash": "Cash",
            "holdings": "Holdings",
            "last_import": "Last Import",
        }

        widths = {
            "brokerage": 140,
            "account_number": 130,
            "name": 220,
            "current_value": 150,
            "cash": 220,
            "holdings": 90,
            "last_import": 180,
        }

        for column in columns:
            self.accounts_tree.heading(
                column,
                text=headings[column],
            )
            self.accounts_tree.column(
                column,
                width=widths[column],
                minwidth=80,
                anchor="w" if column in {
                    "brokerage",
                    "account_number",
                    "name",
                    "cash",
                    "last_import",
                } else "e",
                stretch=True,
            )

        self.accounts_tree.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        scrollbar = ttk.Scrollbar(
            frame,
            orient="vertical",
            command=self.accounts_tree.yview,
        )
        scrollbar.grid(
            row=0,
            column=1,
            sticky="ns",
        )

        self.accounts_tree.configure(
            yscrollcommand=scrollbar.set,
        )

        self.accounts_tree.bind(
            "<<TreeviewSelect>>",
            self._account_selected,
        )
        self.accounts_tree.bind(
            "<Double-1>",
            lambda _event: self._view_holdings(),
        )

        self.status_label = ttk.Label(
            self,
            text="",
        )
        self.status_label.grid(
            row=4,
            column=0,
            sticky="w",
            pady=(8, 0),
        )

    def _load_accounts(self) -> None:
        """Load account summaries from the database."""

        try:
            initialize_database()
            session = get_session()

            try:
                summaries = AccountService(session).get_summaries()
            finally:
                session.close()

            for item in self.accounts_tree.get_children():
                self.accounts_tree.delete(item)

            for summary in summaries:
                self.accounts_tree.insert(
                    "",
                    "end",
                    iid=str(summary.account_id),
                    values=(
                        summary.brokerage_name,
                        summary.account_number,
                        summary.name,
                        self._format_currency(summary.current_value),
                        self._format_cash(summary.cash_by_currency),
                        str(summary.holdings_count),
                        self._format_datetime(summary.last_import),
                    ),
                )

            self.status_label.configure(
                text=f"{len(summaries)} account(s)"
            )

        except Exception as exc:
            self.status_label.configure(text="Unable to load accounts.")
            messagebox.showerror(
                "Accounts",
                f"Unable to load accounts:\n\n"
                f"{type(exc).__name__}: {exc}",
            )

    def _selected_account_id(self) -> int | None:
        """Return the selected account ID."""

        selected = self.accounts_tree.selection()

        if not selected:
            return None

        return int(selected[0])

    def _account_selected(self, _event=None) -> None:
        """Load the two most recent snapshot dates for the selected account."""

        account_id = self._selected_account_id()

        if account_id is None:
            return

        try:
            initialize_database()
            session = get_session()

            try:
                snapshots = session.scalars(
                    select(ImportRecord.snapshot_date)
                    .where(ImportRecord.account_id == account_id)
                    .order_by(ImportRecord.snapshot_date.desc())
                    .limit(2)
                ).all()
            finally:
                session.close()

            if len(snapshots) >= 2:
                self.to_var.set(self._format_date_value(snapshots[0]))
                self.from_var.set(self._format_date_value(snapshots[1]))
            elif len(snapshots) == 1:
                self.to_var.set(self._format_date_value(snapshots[0]))
                self.from_var.set(self._format_date_value(snapshots[0]))
            else:
                self.from_var.set("")
                self.to_var.set("")

        except Exception as exc:
            self.status_label.configure(
                text=(
                    "Unable to load snapshot dates: "
                    f"{type(exc).__name__}: {exc}"
                )
            )

    def _compare_snapshots(self) -> None:
        """Compare the selected account between two snapshot dates."""

        account_id = self._selected_account_id()

        if account_id is None:
            messagebox.showinfo(
                "Compare Snapshots",
                "Select an account first.",
            )
            return

        try:
            first_date = self._parse_date(self.from_var.get())
            second_date = self._parse_date(self.to_var.get())

            if first_date > second_date:
                messagebox.showwarning(
                    "Compare Snapshots",
                    "From date must be on or before To date.",
                )
                return

            initialize_database()
            session = get_session()

            try:
                from src.services.portfolio_comparison_service import (
                    PortfolioComparisonService,
                )

                result = PortfolioComparisonService(session).compare(
                    first_date,
                    second_date,
                    account_id=account_id,
                )
            finally:
                session.close()

            account_values = self.accounts_tree.item(
                str(account_id),
                "values",
            )
            account_name = (
                str(account_values[2])
                if len(account_values) >= 3
                else ""
            )
            account_number = (
                str(account_values[1])
                if len(account_values) >= 2
                else str(account_id)
            )

            self._show_comparison(
                account_number=account_number,
                account_name=account_name,
                first_date=first_date,
                second_date=second_date,
                result=result,
            )

        except ValueError:
            messagebox.showwarning(
                "Compare Snapshots",
                "Enter dates using YYYY-MM-DD.",
            )
        except Exception as exc:
            messagebox.showerror(
                "Compare Snapshots",
                f"Unable to compare snapshots:\n\n"
                f"{type(exc).__name__}: {exc}",
            )

    def _show_comparison(
        self,
        account_number: str,
        account_name: str,
        first_date,
        second_date,
        result,
    ) -> None:
        """Display detailed snapshot comparison results."""

        title_name = (
            f" — {account_name}"
            if account_name and account_name != account_number
            else ""
        )

        window = tk.Toplevel(self)
        window.title(
            f"Snapshot Comparison - Account {account_number}{title_name}"
        )
        window.geometry("1450x650")
        window.minsize(1050, 500)

        window.columnconfigure(0, weight=1)
        window.rowconfigure(2, weight=1)

        ttk.Label(
            window,
            text=(
                f"Account {account_number}{title_name}    "
                f"{first_date:%Y-%m-%d} → {second_date:%Y-%m-%d}"
            ),
            font=("Segoe UI", 13, "bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=15,
            pady=(15, 8),
        )

        summary = ttk.Frame(window)
        summary.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=15,
            pady=(0, 10),
        )

        self._comparison_summary(
            summary,
            "From Value:",
            self._format_currency(result.first_value),
            0,
        )
        self._comparison_summary(
            summary,
            "To Value:",
            self._format_currency(result.second_value),
            2,
        )
        self._comparison_summary(
            summary,
            "Change:",
            self._format_signed_currency(result.value_difference),
            4,
        )

        active = [
            p for p in result.positions
            if p.first_quantity != 0 or p.second_quantity != 0
        ]

        ttk.Label(
            summary,
            text=f"Holdings: {len(active)}",
        ).grid(
            row=0,
            column=6,
            padx=(20, 0),
        )

        frame = ttk.Frame(window)
        frame.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=15,
            pady=(0, 10),
        )
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        columns = (
            "symbol",
            "company",
            "q1",
            "q2",
            "dq",
            "a1",
            "a2",
            "mv1",
            "mv2",
            "g1",
            "g2",
            "status",
        )

        tree = ttk.Treeview(
            frame,
            columns=columns,
            show="headings",
        )

        headings = {
            "symbol": "Symbol",
            "company": "Company",
            "q1": "Qty From",
            "q2": "Qty To",
            "dq": "Qty Change",
            "a1": "Avg Cost From",
            "a2": "Avg Cost To",
            "mv1": "Market Value From",
            "mv2": "Market Value To",
            "g1": "Unrealized Gain From",
            "g2": "Unrealized Gain To",
            "status": "Status",
        }

        widths = {
            "symbol": 100,
            "company": 230,
            "q1": 90,
            "q2": 90,
            "dq": 100,
            "a1": 115,
            "a2": 115,
            "mv1": 140,
            "mv2": 140,
            "g1": 145,
            "g2": 145,
            "status": 100,
        }

        for column in columns:
            tree.heading(
                column,
                text=headings[column],
            )
            tree.column(
                column,
                width=widths[column],
                minwidth=70,
                stretch=False,
                anchor=(
                    "w"
                    if column in {"symbol", "company", "status"}
                    else "e"
                ),
            )

        tree.tag_configure("increase", foreground="green")
        tree.tag_configure("decrease", foreground="red")
        tree.tag_configure("neutral", foreground="black")

        for position in result.positions:
            tag = (
                "increase"
                if position.quantity_difference > 0
                else "decrease"
                if position.quantity_difference < 0
                else "neutral"
            )

            tree.insert(
                "",
                "end",
                values=(
                    position.symbol,
                    position.company_name,
                    self._format_quantity(position.first_quantity),
                    self._format_quantity(position.second_quantity),
                    self._format_signed_quantity(
                        position.quantity_difference
                    ),
                    self._format_currency(
                        position.first_average_cost
                    ),
                    self._format_currency(
                        position.second_average_cost
                    ),
                    self._format_currency(
                        position.first_market_value
                    ),
                    self._format_currency(
                        position.second_market_value
                    ),
                    self._format_signed_currency(
                        position.first_unrealized_gain
                    ),
                    self._format_signed_currency(
                        position.second_unrealized_gain
                    ),
                    position.status,
                ),
                tags=(tag,),
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

        ttk.Button(
            window,
            text="Close",
            command=window.destroy,
        ).grid(
            row=3,
            column=0,
            sticky="e",
            padx=15,
            pady=(0, 15),
        )

    @staticmethod
    def _comparison_summary(
        parent,
        label: str,
        value: str,
        column: int,
    ) -> None:
        ttk.Label(
            parent,
            text=label,
            font=("Segoe UI", 10, "bold"),
        ).grid(
            row=0,
            column=column,
            sticky="e",
        )
        ttk.Label(
            parent,
            text=value,
        ).grid(
            row=0,
            column=column + 1,
            sticky="w",
            padx=(5, 0),
        )

    @staticmethod
    def _parse_date(value: str):
        from datetime import datetime

        return datetime.strptime(
            value.strip(),
            "%Y-%m-%d",
        ).date()

    @staticmethod
    def _format_date_value(value) -> str:
        if hasattr(value, "date"):
            value = value.date()

        return value.strftime("%Y-%m-%d")

    def _rename_account(self) -> None:
        """Rename the selected account."""

        account_id = self._selected_account_id()

        if account_id is None:
            messagebox.showinfo(
                "Rename Account",
                "Select an account first.",
            )
            return

        values = self.accounts_tree.item(
            str(account_id),
            "values",
        )

        current_name = str(values[2])
        account_number = str(values[1])

        new_name = simpledialog.askstring(
            "Rename Account",
            f"Account {account_number}:",
            initialvalue=current_name,
            parent=self,
        )

        if new_name is None:
            return

        try:
            initialize_database()
            session = get_session()

            try:
                AccountService(session).rename(
                    account_id,
                    new_name,
                )
            finally:
                session.close()

            self._load_accounts()

        except Exception as exc:
            messagebox.showerror(
                "Rename Account",
                f"Unable to rename account:\n\n"
                f"{type(exc).__name__}: {exc}",
            )

    def _view_holdings(self) -> None:
        """Open the current holdings for the selected account."""

        account_id = self._selected_account_id()

        if account_id is None:
            messagebox.showinfo(
                "View Holdings",
                "Select an account first.",
            )
            return

        # Import lazily to avoid coupling AccountsTab to PortfolioTab
        # during application startup.
        from src.services.portfolio_service import PortfolioService

        try:
            initialize_database()
            session = get_session()

            try:
                portfolio = PortfolioService(
                    session
                ).get_latest_portfolio(account_id)
            finally:
                session.close()

            if portfolio is None:
                messagebox.showinfo(
                    "View Holdings",
                    "No imported portfolio exists for this account.",
                )
                return

            window = tk.Toplevel(self)
            window.title(
                f"Holdings - Account {self.accounts_tree.item(str(account_id), 'values')[1]}"
            )
            window.geometry("1050x600")
            window.minsize(850, 450)

            window.columnconfigure(0, weight=1)
            window.rowconfigure(1, weight=1)

            ttk.Label(
                window,
                text=(
                    f"Snapshot: "
                    f"{portfolio.snapshot_date:%Y-%m-%d %H:%M:%S}"
                ),
                font=("Segoe UI", 11),
            ).grid(
                row=0,
                column=0,
                sticky="w",
                padx=15,
                pady=12,
            )

            frame = ttk.Frame(window)
            frame.grid(
                row=1,
                column=0,
                sticky="nsew",
                padx=15,
                pady=(0, 15),
            )
            frame.columnconfigure(0, weight=1)
            frame.rowconfigure(0, weight=1)

            columns = (
                "symbol",
                "company",
                "quantity",
                "average_cost",
                "price",
                "market_value",
                "unrealized_gain",
            )

            tree = ttk.Treeview(
                frame,
                columns=columns,
                show="headings",
            )

            headings = {
                "symbol": "Symbol",
                "company": "Company",
                "quantity": "Quantity",
                "average_cost": "Avg Cost",
                "price": "Price",
                "market_value": "Market Value",
                "unrealized_gain": "Unrealized Gain",
            }

            for column in columns:
                tree.heading(
                    column,
                    text=headings[column],
                )

            tree.column("symbol", width=100, anchor="w")
            tree.column("company", width=250, anchor="w")
            tree.column("quantity", width=110, anchor="e")
            tree.column("average_cost", width=120, anchor="e")
            tree.column("price", width=110, anchor="e")
            tree.column("market_value", width=140, anchor="e")
            tree.column("unrealized_gain", width=150, anchor="e")

            for holding in sorted(
                portfolio.holdings,
                key=lambda item: item.symbol,
            ):
                tree.insert(
                    "",
                    "end",
                    values=(
                        holding.symbol,
                        holding.company_name,
                        self._format_quantity(holding.quantity),
                        self._format_currency(
                            holding.average_cost
                        ),
                        self._format_currency(holding.price),
                        self._format_currency(
                            holding.market_value
                        ),
                        self._format_signed_currency(
                            holding.unrealized_gain
                        ),
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

            ttk.Button(
                window,
                text="Close",
                command=window.destroy,
            ).grid(
                row=2,
                column=0,
                sticky="e",
                padx=15,
                pady=(0, 15),
            )

        except Exception as exc:
            messagebox.showerror(
                "View Holdings",
                f"Unable to load holdings:\n\n"
                f"{type(exc).__name__}: {exc}",
            )

    @staticmethod
    def _format_signed_quantity(
        value: Decimal | None,
    ) -> str:
        """Format a signed security quantity."""

        if value is None:
            return "--"

        if value == 0:
            return "0"

        sign = "+" if value > 0 else "-"
        return sign + AccountsTab._format_quantity(abs(value))

    @staticmethod
    def _format_currency(
        value: Decimal | None,
    ) -> str:
        """Format a CAD value."""

        if value is None:
            return "--"

        return f"${value:,.2f}"

    @staticmethod
    def _format_signed_currency(
        value: Decimal | None,
    ) -> str:
        """Format a signed currency value."""

        if value is None:
            return "--"

        return f"{value:+,.2f}"

    @staticmethod
    def _format_quantity(
        value: Decimal | None,
    ) -> str:
        """Format a security quantity."""

        if value is None:
            return "--"

        if value == value.to_integral_value():
            return f"{int(value):,}"

        return f"{value:,.6f}".rstrip("0").rstrip(".")

    @staticmethod
    def _format_cash(
        cash_by_currency: dict[str, Decimal],
    ) -> str:
        """Format cash balances by currency."""

        if not cash_by_currency:
            return "--"

        parts = []

        for currency in sorted(cash_by_currency):
            parts.append(
                f"{currency} ${cash_by_currency[currency]:,.2f}"
            )

        return " / ".join(parts)

    @staticmethod
    def _format_datetime(
        value,
    ) -> str:
        """Format the last import timestamp."""

        if value is None:
            return "--"

        return value.strftime("%Y-%m-%d %H:%M:%S")
