"""
Portfolio tab for the Financial Model GUI.
"""

import queue
import threading
import tkinter as tk
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from tkinter import messagebox, ttk

from sqlalchemy import select, func

from src.database import get_session
from src.database_init import initialize_database
from src.gui.accounts_tab import AccountsTab
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
        self.rowconfigure(4, weight=1)

        # Portfolio valuation runs in a worker thread so the Tkinter event
        # loop remains responsive while Yahoo Finance requests are in progress.
        self._update_queue: queue.Queue = queue.Queue()
        self._update_thread: threading.Thread | None = None
        self._update_running = False

        self._build_ui()

        # Refresh immediately when an account is included or excluded.
        self.winfo_toplevel().bind(
            "<<AccountSettingsChanged>>",
            self._on_account_settings_changed,
            add="+",
        )

        # Load existing values when the tab is created.
        self.after(100, self._load_current_values)

    def _on_account_settings_changed(self, _event=None) -> None:
        """Refresh the displayed portfolio after account inclusion changes."""
        self._load_current_values()

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

        self.update_button = ttk.Button(
            controls,
            text="Update Portfolio",
            command=self._update_portfolio,
        )
        self.update_button.pack(side="left")

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

        self.last_update_label = ttk.Label(
            summary,
            text="Last Updated: --",
            font=("Segoe UI", 9),
        )

        self.last_update_label.grid(
            row=1,
            column=0,
            columnspan=4,
            sticky="e",
            padx=(10, 10),
            pady=(8, 0),
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
        # The Accounts view is embedded here so Portfolio is the
        # single authoritative account screen. It retains account
        # type, Include, rename, snapshot comparison, cash,
        # holdings, current value, Today, ROI, and last import.
        self.accounts_page = AccountsTab(self)
        self.accounts_page.grid(
            row=5,
            column=0,
            sticky="nsew",
            pady=(0, 5),
        )

    # =============================================================
    # Update
    # =============================================================

    def _update_portfolio(self) -> None:
        """Start a portfolio update without blocking the Tkinter UI thread."""

        if self._update_running:
            return

        self._update_running = True
        self.update_button.configure(state="disabled")
        self.status_label.configure(text="Updating...")
        self.progress_bar.configure(value=0)
        self.progress_label.configure(
            text="Updating Portfolio: 0%   0 / 0   Starting..."
        )
        self.update_idletasks()

        self._update_thread = threading.Thread(
            target=self._run_portfolio_update_worker,
            name="portfolio-update",
            daemon=True,
        )
        self._update_thread.start()

        # Poll the thread-safe queue from Tkinter's main thread.  All widget
        # updates happen here, never from the worker thread.
        self.after(50, self._poll_update_queue)

    def _run_portfolio_update_worker(self) -> None:
        """Perform the long-running valuation work on a background thread."""

        session = None

        try:
            initialize_database()
            session = get_session()

            service = PortfolioValuationService(
                session,
                progress_callback=self._queue_update_progress,
            )

            total_value = service.update_all_accounts()
            tsx_change = getattr(
                service,
                "tsx_daily_change_percent",
                None,
            )

            self._update_queue.put(
                ("complete", total_value, tsx_change)
            )

        except Exception as exc:
            # Pass only simple values between threads.  The exception itself
            # is deliberately not used by the GUI worker after this point.
            self._update_queue.put(
                ("error", type(exc).__name__, str(exc))
            )

        finally:
            if session is not None:
                session.close()

    def _queue_update_progress(
        self,
        count: int,
        total: int,
        symbol: str,
    ) -> None:
        """Queue a progress update for the Tkinter main thread."""

        self._update_queue.put(("progress", count, total, symbol))

    def _poll_update_queue(self) -> None:
        """Apply queued worker results and progress updates on the UI thread."""

        try:
            while True:
                message = self._update_queue.get_nowait()
                message_type = message[0]

                if message_type == "progress":
                    _, count, total, symbol = message
                    self._show_update_progress(count, total, symbol)
                    continue

                if message_type == "complete":
                    _, total_value, tsx_change = message
                    self._finish_portfolio_update(
                        total_value,
                        tsx_change,
                    )
                    return

                if message_type == "error":
                    _, error_type, error_text = message
                    self._fail_portfolio_update(
                        error_type,
                        error_text,
                    )
                    return

        except queue.Empty:
            pass

        if self._update_running:
            self.after(50, self._poll_update_queue)

    def _show_update_progress(
        self,
        count: int,
        total: int,
        symbol: str,
    ) -> None:
        """Display queued portfolio update progress."""

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

    def _update_progress(
        self,
        count: int,
        total: int,
        symbol: str,
    ) -> None:
        """Compatibility wrapper that queues progress safely."""

        self._queue_update_progress(count, total, symbol)

    def _finish_portfolio_update(
        self,
        total_value: Decimal,
        tsx_change: Decimal | None,
    ) -> None:
        """Finish a successful update on the Tkinter main thread."""

        self._update_running = False
        self.update_button.configure(state="normal")

        self._load_current_values(tsx_change=tsx_change)

        self.progress_bar.configure(value=100)
        self.progress_label.configure(
            text=(
                "Updating Portfolio: 100%   Complete   "
                f"TOTAL: {self._format_currency(total_value)}"
            )
        )

        self.status_label.configure(
            text=f"Updated: {self._format_currency(total_value)}"
        )

        # Notify the Accounts tab that the portfolio snapshots have been
        # updated. Accounts listens for this event and reloads its values
        # automatically, so a manual Refresh is not needed.
        self.event_generate("<<PortfolioUpdated>>", when="tail")

    def _fail_portfolio_update(
        self,
        error_type: str,
        error_text: str,
    ) -> None:
        """Finish a failed update on the Tkinter main thread."""

        self._update_running = False
        self.update_button.configure(state="normal")

        self.progress_label.configure(
            text=f"Update failed: {error_type}: {error_text}"
        )
        self.progress_bar.configure(value=0)
        self.status_label.configure(text="Update failed.")

        messagebox.showerror(
            "Portfolio Update Error",
            f"{error_type}: {error_text}",
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

                # The persisted consolidated snapshot is still used for
                # TSX and valuation timestamp.  Portfolio totals themselves
                # are derived from today's account snapshots and the account
                # inclusion flag, so changing an account's inclusion setting
                # takes effect immediately without requiring another market
                # price update.
                consolidated = session.scalar(
                    select(PortfolioSnapshot)
                    .where(
                        PortfolioSnapshot.account_id.is_(None),
                        PortfolioSnapshot.snapshot_date == today,
                    )
                )

                included_account_count = session.scalar(
                    select(func.count(Account.id)).where(
                        Account.include_in_portfolio.is_(True),
                    )
                ) or 0

                # Calculate the displayed portfolio value and today's
                # gain/loss from the included accounts' cached snapshots.
                #
                # Do not use the consolidated snapshot for these figures:
                # the consolidated snapshot represents the inclusion state
                # at the time of the last Portfolio Update and therefore
                # cannot reflect a checkbox change.
                included_rows = session.execute(
                    select(
                        Account.id,
                        PortfolioSnapshot.total_value,
                    )
                    .join(
                        PortfolioSnapshot,
                        PortfolioSnapshot.account_id == Account.id,
                    )
                    .where(
                        PortfolioSnapshot.snapshot_date == today,
                        Account.include_in_portfolio.is_(True),
                    )
                ).all()

                if not included_rows:
                    total_value = Decimal("0")
                    total_change = Decimal("0")
                    total_percent = Decimal("0")
                else:
                    total_value = sum(
                        (
                            Decimal(str(row.total_value))
                            for row in included_rows
                        ),
                        Decimal("0"),
                    )

                    # Use the same daily-change calculation used for each
                    # account row below.  This handles snapshots where the
                    # daily_change column is missing or was created before
                    # that field was populated, while still using only data
                    # already stored in the database.
                    total_change = Decimal("0")
                    have_daily_change = False

                    for row in included_rows:
                        account_change, _ = self._calculate_daily_change(
                            row.id,
                            session=session,
                        )

                        if account_change is not None:
                            total_change += Decimal(str(account_change))
                            have_daily_change = True

                    if have_daily_change:
                        total_percent = (
                            self._daily_change_percent_from_values(
                                total_value,
                                total_change,
                            )
                        )
                    else:
                        total_change = None
                        total_percent = None

                self.total_value_label.configure(
                    text=self._format_currency(total_value)
                )

                if total_change is None:
                    self.total_change_label.configure(
                        text="Today: --",
                        foreground="black",
                    )
                else:
                    self.total_change_label.configure(
                        text=(
                            "Today: "
                            f"{self._format_signed_currency(total_change)} "
                            f"({self._format_percent(total_percent)})"
                        ),
                        foreground=(
                            "green" if total_change > 0
                            else "red" if total_change < 0
                            else "black"
                        ),
                    )

                # -------------------------------------------------
                # TSX and last update
                # -------------------------------------------------

                # These values are persisted in the consolidated snapshot.
                # On application startup there is no valuation service in
                # memory, so do not depend on the transient tsx_change
                # argument here.
                saved_tsx = getattr(
                    consolidated,
                    "tsx_daily_change_percent",
                    None,
                )

                if saved_tsx is None:
                    self.tsx_label.configure(
                        text="TSX: --",
                        foreground="black",
                    )
                else:
                    saved_tsx = Decimal(str(saved_tsx))
                    self.tsx_label.configure(
                        text=(
                            "TSX: "
                            f"{self._format_percent(saved_tsx)}"
                        ),
                        foreground=(
                            "green" if saved_tsx > 0
                            else "red" if saved_tsx < 0
                            else "black"
                        ),
                    )

                updated_at = getattr(
                    consolidated,
                    "valuation_updated_at",
                    None,
                )

                if updated_at is None:
                    self.last_update_label.configure(
                        text="Last Updated: --"
                    )
                else:
                    self.last_update_label.configure(
                        text=(
                            "Last Updated: "
                            f"{updated_at.strftime('%Y-%m-%d %I:%M:%S %p')}"
                        )
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
                Account.include_in_portfolio.is_(True),
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

            self.brokerage_tree.insert(
                "",
                "end",
                values=(
                    brokerage_name,
                    self._format_currency(value),
                    today_text,
                ),
                tags=(
                    "today_positive"
                    if change is not None and change > 0
                    else "today_negative"
                    if change is not None and change < 0
                    else "today_zero"
                ),
            )

    # =============================================================
    # Daily change
    # =============================================================

    @staticmethod
    def _daily_change_percent_from_values(
        current_value: Decimal,
        daily_change: Decimal,
    ) -> Decimal:
        """Calculate a daily percentage from current value and change."""
        previous_value = current_value - daily_change

        if previous_value == 0:
            return Decimal("0")

        return daily_change / previous_value * Decimal("100")

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