"""
Portfolio tab for the Financial Model GUI.
"""

import tkinter as tk
from datetime import date, timedelta
from decimal import Decimal
from tkinter import messagebox, ttk

from sqlalchemy import select, func

from src.database import get_session
from src.database_init import initialize_database
from src.models.account import Account
from src.models.brokerage import Brokerage
from src.models.portfolio_snapshot import PortfolioSnapshot
from src.services.portfolio_valuation_service import (
    PortfolioValuationService,
)


class PortfolioTab(ttk.Frame):
    """Display current portfolio values."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        # Values calculated by the most recent portfolio update.
        self._last_total_change: Decimal | None = None
        self._last_total_change_percent: Decimal | None = None
        self._last_account_changes: dict[int, tuple[Decimal, Decimal]] = {}
        self._last_brokerage_changes: dict[int, tuple[Decimal, Decimal]] = {}
        self._last_tsx_change: Decimal | None = None

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

        progress_frame = ttk.LabelFrame(
            self,
            text="Update Progress",
            padding=8,
        )

        progress_frame.grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(0, 15),
        )

        progress_frame.columnconfigure(0, weight=1)

        self.progress_bar = ttk.Progressbar(
            progress_frame, orient="horizontal", mode="determinate", maximum=100
        )
        self.progress_bar.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.progress_percent_label = ttk.Label(
            progress_frame, text="0%", width=5, anchor="e"
        )
        self.progress_percent_label.grid(row=0, column=1, sticky="e")

        self.progress_status_label = ttk.Label(
            progress_frame, text="Ready."
        )
        self.progress_status_label.grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(6, 0)
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

    # =============================================================
    # Update
    # =============================================================

    def _update_portfolio(self) -> None:
        """Update all account and consolidated portfolio values."""

        self.status_label.configure(text="Updating...")
        self.progress_bar.configure(maximum=100, value=0)
        self.progress_percent_label.configure(text="0%")
        self.progress_status_label.configure(text="Preparing price lookups...")
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
                # service while they are still available. These are
                # especially important on the first valuation day,
                # when there is no previous PortfolioSnapshot yet.
                self._last_total_change = getattr(
                    service,
                    "total_daily_change",
                    None,
                )
                self._last_total_change_percent = getattr(
                    service,
                    "total_daily_change_percent",
                    None,
                )
                self._last_account_changes = {
                    account_id: (
                        change,
                        getattr(
                            service,
                            "account_daily_change_percents",
                        ).get(account_id, Decimal("0")),
                    )
                    for account_id, change in getattr(
                        service,
                        "account_daily_changes",
                        {},
                    ).items()
                }
                self._last_brokerage_changes = {
                    brokerage_id: (
                        change,
                        getattr(
                            service,
                            "brokerage_daily_change_percents",
                        ).get(brokerage_id, Decimal("0")),
                    )
                    for brokerage_id, change in getattr(
                        service,
                        "brokerage_daily_changes",
                        {},
                    ).items()
                }
                tsx_change = getattr(
                    service,
                    "tsx_daily_change_percent",
                    None,
                )
                self._last_tsx_change = tsx_change

            finally:
                session.close()

            self._load_current_values(
                tsx_change=tsx_change
            )

            self.status_label.configure(
                text=(
                    f"Updated: "
                    f"{self._format_currency(total_value)}"
                )
            )

            self.progress_bar.configure(
                maximum=max(int(float(self.progress_bar["maximum"])), 1),
                value=self.progress_bar["maximum"],
            )
            self.progress_percent_label.configure(text="100%")
            self.progress_status_label.configure(text="Update complete.")
            self.update_idletasks()

        except Exception as exc:
            self.status_label.configure(
                text="Update failed."
            )

            self.progress_status_label.configure(
                text=f"Update failed: {type(exc).__name__}"
            )
            self.update_idletasks()

            messagebox.showerror(
                "Portfolio Update Error",
                f"{type(exc).__name__}: {exc}",
            )

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

                if tsx_change is None:
                    tsx_change = self._last_tsx_change

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

            self.accounts_tree.insert(
                "",
                "end",
                values=(
                    brokerage_name,
                    account.account_number,
                    account.name,
                    self._format_currency(value),
                    today_text,
                    self._format_percent(roi),
                ),
            )

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
                cached = self._last_brokerage_changes.get(brokerage_id)
                if cached is None:
                    change = None
                    change_percent = None
                else:
                    change, change_percent = cached
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

            self.brokerage_tree.insert(
                "",
                "end",
                values=(
                    brokerage_name,
                    self._format_currency(value),
                    today_text,
                ),
            )

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
                # On the first valuation day there is no previous
                # PortfolioSnapshot. Use the market-price change
                # calculated during the update instead.
                if account_id is None:
                    if self._last_total_change is not None:
                        return (
                            self._last_total_change,
                            self._last_total_change_percent,
                        )
                else:
                    cached = self._last_account_changes.get(account_id)
                    if cached is not None:
                        return cached
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

    def _update_progress(self, current: int, total: int, symbol: str) -> None:
        """Update the price lookup progress display."""
        percent = 100 if total <= 0 else (current / total) * 100
        self.progress_bar.configure(maximum=total if total > 0 else 1, value=current)
        self.progress_percent_label.configure(text=f"{percent:.0f}%")
        self.progress_status_label.configure(
            text=f"Looking up {current} of {total}: {symbol}"
        )
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