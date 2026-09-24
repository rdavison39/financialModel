"""
Graphs tab for the Financial Model GUI.
"""

import tkinter as tk
from datetime import date, timedelta
from decimal import Decimal
from tkinter import ttk

from sqlalchemy import select

from src.database import get_session
from src.database_init import initialize_database
from src.models.account import Account
from src.models.brokerage import Brokerage
from src.services.portfolio_history_service import (
    PortfolioHistoryPoint,
    PortfolioHistoryService,
)
from src.services.ui_settings_service import UISettingsService


class GraphsTab(ttk.Frame):
    """Display historical portfolio values for selected accounts."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)

        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=5)
        self.rowconfigure(2, weight=1)

        self._account_names: dict[int, str] = {}
        self._account_vars: dict[int, tk.BooleanVar] = {}
        self._last_history: list[PortfolioHistoryPoint] = []
        self._last_benchmark = []
        self._benchmark_previous_value = None
        self._navigation_account_frame: ttk.LabelFrame | None = None
        self._history_frame: ttk.LabelFrame | None = None
        self._ui_settings = UISettingsService()
        self._restoring_ui_settings = False

        self._build_ui()
        self._build_navigation_account_selector()
        for variable in (
            self.view_mode,
            self.period,
            self.benchmark,
            self.custom_benchmark,
            self.start_date,
            self.end_date,
        ):
            variable.trace_add("write", self._ui_setting_changed)

        # Load accounts and the default date range when the tab is created.
        self.after(100, self._initialize)

        # The account selector belongs to the application's left navigation
        # area.  Show it only while the Graphs page is visible.
        self.bind("<Map>", self._show_navigation_account_selector, add="+")
        self.bind("<Unmap>", self._hide_navigation_account_selector, add="+")
        self.winfo_toplevel().bind("<Configure>", self._on_window_configure, add="+")

    # -------------------------------------------------------------
    # UI
    # -------------------------------------------------------------

    def _build_ui(self) -> None:
        """Build the Portfolio History page."""

        ttk.Label(
            self,
            text="Portfolio History",
            font=("Segoe UI", 18, "bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 15),
        )

        controls = ttk.Frame(self)
        controls.grid(
            row=0,
            column=1,
            sticky="nw",
            padx=(20, 0),
            pady=(0, 15),
        )

        # View
        ttk.Label(controls, text="View:").grid(
            row=0, column=0, padx=(0, 5)
        )

        self.view_mode = tk.StringVar(value="Portfolio Value")
        view_combo = ttk.Combobox(
            controls,
            textvariable=self.view_mode,
            values=(
                "Portfolio Value",
                "% Growth Since Start",
                "Day's Gain/Loss",
                "% Day's Gain/Loss",
            ),
            state="readonly",
            width=15,
            height=5,
        )
        view_combo.grid(row=0, column=1, padx=(0, 12))
        view_combo.bind("<<ComboboxSelected>>", self._view_changed)

        # Period
        ttk.Label(controls, text="Period:").grid(
            row=0, column=2, padx=(0, 5)
        )

        self.period = tk.StringVar(value="1 Year")
        period_combo = ttk.Combobox(
            controls,
            textvariable=self.period,
            values=(
                "1 Month",
                "3 Months",
                "6 Months",
                "YTD",
                "1 Year",
                "3 Years",
                "5 Years",
                "All Time",
                "Custom",
            ),
            state="readonly",
            width=12,
        )
        period_combo.grid(row=0, column=3, padx=(0, 12))
        period_combo.bind("<<ComboboxSelected>>", self._period_changed)

        # Benchmark
        ttk.Label(controls, text="Benchmark:").grid(
            row=0, column=4, padx=(0, 5)
        )

        self.benchmark = tk.StringVar(value="TSX Composite")
        benchmark_combo = ttk.Combobox(
            controls,
            textvariable=self.benchmark,
            values=(
                "None",
                "S&P 500",
                "TSX Composite",
                "Custom",
            ),
            state="readonly",
            width=14,
        )
        benchmark_combo.grid(row=0, column=5, padx=(0, 5))
        benchmark_combo.bind("<<ComboboxSelected>>", self._benchmark_changed)
        self.benchmark_combo = benchmark_combo

        self.custom_benchmark = tk.StringVar(value="")
        self.custom_benchmark_entry = ttk.Entry(
            controls,
            textvariable=self.custom_benchmark,
            width=12,
        )
        self.custom_benchmark_entry.grid(
            row=0,
            column=6,
            padx=(0, 12),
        )
        self.custom_benchmark_entry.grid_remove()
        self.custom_benchmark_entry.bind(
            "<Return>",
            lambda _event: self._refresh(),
        )
        self._update_benchmark_state()

        # Dates
        ttk.Label(controls, text="Start:").grid(
            row=1, column=0, padx=(0, 5), pady=(8, 0)
        )

        self.start_date = tk.StringVar(value=(date.today() - timedelta(days=365)).isoformat())
        ttk.Entry(
            controls,
            textvariable=self.start_date,
            width=12,
        ).grid(row=1, column=1, padx=(0, 12), pady=(8, 0))

        ttk.Label(controls, text="End:").grid(
            row=1, column=2, padx=(0, 5), pady=(8, 0)
        )

        self.end_date = tk.StringVar(value=date.today().isoformat())
        ttk.Entry(
            controls,
            textvariable=self.end_date,
            width=12,
        ).grid(row=1, column=3, padx=(0, 12), pady=(8, 0))

        ttk.Button(
            controls,
            text="Refresh",
            command=self._refresh,
        ).grid(row=1, column=4, columnspan=3, pady=(8, 0), sticky="e")

        graph_frame = ttk.LabelFrame(
            self,
            text="Portfolio History",
            padding=10,
        )
        graph_frame.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="nsew",
            pady=(0, 15),
        )
        graph_frame.columnconfigure(0, weight=1)
        graph_frame.rowconfigure(0, weight=1)

        self.graph_canvas = tk.Canvas(
            graph_frame,
            height=450,
            background="white",
            highlightthickness=1,
        )
        self.graph_canvas.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        history_frame = ttk.LabelFrame(
            self,
            text="History",
            padding=10,
        )
        self._history_frame = history_frame

        history_frame.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="nsew",
        )
        history_frame.columnconfigure(0, weight=1)
        history_frame.rowconfigure(0, weight=1)

        self.history_tree = ttk.Treeview(
            history_frame,
            columns=("date", "value", "change"),
            show="headings",
            height=6,
        )

        self.history_tree.heading("date", text="Date")
        self.history_tree.heading("value", text="Portfolio Value")
        self.history_tree.heading("change", text="Change")

        self.history_tree.column("date", width=150)
        self.history_tree.column(
            "value",
            width=200,
            anchor="e",
        )
        self.history_tree.column(
            "change",
            width=200,
            anchor="e",
        )

        self.history_tree.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        scrollbar = ttk.Scrollbar(
            history_frame,
            orient="vertical",
            command=self.history_tree.yview,
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.history_tree.configure(yscrollcommand=scrollbar.set)

        self.status_label = ttk.Label(self, text="")
        self.status_label.grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(8, 0),
        )

        self.graph_canvas.bind(
            "<Configure>",
            self._on_graph_resize,
        )

    # -------------------------------------------------------------
    # Navigation account selector
    # -------------------------------------------------------------

    def _build_navigation_account_selector(self) -> None:
        """Create the account checklist below the left navigation buttons."""
        navigation = self._find_navigation_frame()
        if navigation is None:
            return

        frame_background = ttk.Style().lookup("TFrame", "background") or "white"

        self._navigation_account_frame = ttk.LabelFrame(
            navigation,
            text="Accounts to Graph",
            width=235,
            height=500,
            padding=5,
        )
        self._navigation_account_frame.pack(fill="x", pady=(10, 0))
        self._navigation_account_frame.pack_propagate(False)

        controls = ttk.Frame(self._navigation_account_frame)
        controls.pack(fill="x", pady=(0, 4))

        ttk.Button(controls, text="All", command=self._check_all, width=5).pack(side="left")
        ttk.Button(controls, text="None", command=self._uncheck_all, width=6).pack(side="left", padx=(4, 0))

        self.selected_accounts_label = ttk.Label(controls, text="0/0")
        self.selected_accounts_label.pack(side="right")

        list_frame = ttk.Frame(self._navigation_account_frame)
        list_frame.pack(fill="both", expand=True)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.account_canvas = tk.Canvas(
            list_frame, highlightthickness=0, background=frame_background, width=215
        )
        self.account_canvas.grid(row=0, column=0, sticky="nsew")

        self.account_inner = ttk.Frame(self.account_canvas)
        self.account_window = self.account_canvas.create_window(
            0, 0, window=self.account_inner, anchor="nw"
        )

        self.account_scrollbar = ttk.Scrollbar(
            list_frame, orient="vertical", command=self.account_canvas.yview
        )
        self.account_scrollbar.grid(row=0, column=1, sticky="ns")

        self.account_hscrollbar = ttk.Scrollbar(
            list_frame, orient="horizontal", command=self.account_canvas.xview
        )
        self.account_hscrollbar.grid(row=1, column=0, sticky="ew")

        self.account_canvas.configure(
            yscrollcommand=self.account_scrollbar.set,
            xscrollcommand=self.account_hscrollbar.set,
        )
        self.account_inner.bind("<Configure>", self._on_account_list_configure)
        self.account_canvas.bind("<Configure>", self._on_account_canvas_configure)
        self._navigation_account_frame.pack_forget()

    def _find_navigation_frame(self) -> ttk.Frame | None:
        """Find the shared navigation frame without depending on button names."""
        root = self.winfo_toplevel()
        navigation_labels = {
            "Portfolio",
            "Portfolio History",
            "Account Management",
            "Account History",
            "Holdings History",
            "Import",
        }

        def walk(widget: tk.Misc) -> ttk.Frame | None:
            for child in widget.winfo_children():
                if isinstance(child, ttk.Button):
                    try:
                        if child.cget("text") in navigation_labels:
                            parent = child.nametowidget(child.winfo_parent())
                            if isinstance(parent, ttk.Frame):
                                return parent
                    except tk.TclError:
                        pass
                found = walk(child)
                if found is not None:
                    return found
            return None

        return walk(root)

    def _on_window_configure(self, _event=None) -> None:
        """Keep the navigation account selector aligned with the history table."""
        if self.winfo_ismapped():
            self.after_idle(self._sync_navigation_account_height)

    def _sync_navigation_account_height(self) -> None:
        """Extend the account selector down to the bottom of the history table."""
        frame = self._navigation_account_frame
        history = self._history_frame
        if frame is None or history is None or not frame.winfo_ismapped():
            return

        self.update_idletasks()
        history_bottom = history.winfo_rooty() + history.winfo_height()
        frame_top = frame.winfo_rooty()
        desired_height = history_bottom - frame_top - 4
        if desired_height > 100:
            frame.configure(height=desired_height)

    def _show_navigation_account_selector(self, _event=None) -> None:
        """Show the account selector when Portfolio History becomes visible."""
        if self._navigation_account_frame is not None:
            self._navigation_account_frame.pack(fill="x", pady=(10, 0))
            self.after_idle(self._sync_navigation_account_height)

    def _hide_navigation_account_selector(self, _event=None) -> None:
        """Hide the account selector when leaving Portfolio History."""
        if self._navigation_account_frame is not None:
            self._navigation_account_frame.pack_forget()

    def _on_account_list_configure(self, _event) -> None:
        """Update the account selector's scroll region."""
        self.account_canvas.configure(scrollregion=self.account_canvas.bbox("all"))

    def _update_account_scroll_region(self) -> None:
        """Recalculate the account selector's scrollable area."""
        self.account_canvas.configure(scrollregion=self.account_canvas.bbox("all"))

    def _on_account_canvas_configure(self, event) -> None:
        """Keep the account selector content wide enough for long names."""
        self.account_inner.update_idletasks()
        requested_width = self.account_inner.winfo_reqwidth()
        self.account_canvas.itemconfigure(
            self.account_window, width=max(requested_width, event.width)
        )
        self._update_account_scroll_region()

    # -------------------------------------------------------------
    # Refresh
    # -------------------------------------------------------------

    def _initialize(self) -> None:
        """Load accounts and initialize the default one-year period."""
        if self._navigation_account_frame is None:
            self.status_label.configure(
                text="Unable to locate the navigation account selector."
            )
            return

        try:
            initialize_database()
            session = get_session()
            try:
                rows = session.execute(
                    select(Account, Brokerage)
                    .join(
                        Brokerage,
                        Account.brokerage_id == Brokerage.id,
                    )
                    .order_by(
                        Brokerage.name,
                        Account.account_number,
                    )
                ).all()
            finally:
                session.close()

            for child in self.account_inner.winfo_children():
                child.destroy()

            self._account_names.clear()
            self._account_vars.clear()

            for index, (account, brokerage) in enumerate(rows):
                full_name = (
                    f"{brokerage.name} - "
                    f"{account.account_number} - "
                    f"{account.name}"
                )

                variable = tk.BooleanVar(value=True)
                self._account_names[account.id] = full_name
                self._account_vars[account.id] = variable

                ttk.Checkbutton(
                    self.account_inner,
                    text=full_name,
                    variable=variable,
                    command=self._selection_changed,
                ).grid(
                    row=index,
                    column=0,
                    sticky="w",
                    padx=0,
                    pady=1,
                )

            self.account_inner.columnconfigure(0, weight=1)
            self._update_selected_accounts_label()
            self._update_account_scroll_region()

            self._restore_ui_settings()
            self._update_selected_accounts_label()
            self._refresh()

        except Exception as exc:
            self.status_label.configure(
                text=f"Error loading accounts: {type(exc).__name__}: {exc}"
            )

    def _period_changed(self, _event=None) -> None:
        """Apply the selected period to the date fields."""
        period = self.period.get()

        if period != "Custom":
            self._set_period_dates(period)

        self._save_ui_settings()
        self._refresh()

    def _set_period_dates(self, period: str) -> None:
        """Set start/end dates for a named period."""
        end = date.today()

        if period == "1 Month":
            start = end - timedelta(days=30)
        elif period == "3 Months":
            start = end - timedelta(days=91)
        elif period == "6 Months":
            start = end - timedelta(days=182)
        elif period == "YTD":
            start = date(end.year, 1, 1)
        elif period == "1 Year":
            start = end - timedelta(days=365)
        elif period == "3 Years":
            start = end - timedelta(days=365 * 3)
        elif period == "5 Years":
            start = end - timedelta(days=365 * 5)
        elif period == "All Time":
            start = date(2000, 1, 1)
        else:
            return

        self.start_date.set(start.isoformat())
        self.end_date.set(end.isoformat())

    def _view_changed(self, _event=None) -> None:
        """Refresh after changing the history metric."""
        self._update_benchmark_state()
        self._refresh()

    def _benchmark_changed(self, _event=None) -> None:
        """Show custom symbol entry only when the selected view supports benchmarks."""
        if not self._benchmark_is_supported():
            self.benchmark.set("None")

        if self.benchmark.get() == "Custom" and self._benchmark_is_supported():
            self.custom_benchmark_entry.grid()
        else:
            self.custom_benchmark_entry.grid_remove()

        self._save_ui_settings()
        self._refresh()

    def _benchmark_is_supported(self) -> bool:
        """Return whether the current view can meaningfully use a benchmark."""
        return self.view_mode.get() in {"% Growth Since Start", "% Day's Gain/Loss"}

    def _update_benchmark_state(self) -> None:
        """Enable benchmarks only for percentage-based comparison views."""
        if self._benchmark_is_supported():
            self.benchmark_combo.configure(state="readonly")
            if self.benchmark.get() == "Custom" and self.custom_benchmark.get().strip():
                self.custom_benchmark_entry.grid()
            else:
                self.custom_benchmark_entry.grid_remove()
        else:
            self.benchmark.set("None")
            self.benchmark_combo.configure(state="disabled")
            self.custom_benchmark_entry.grid_remove()

    def _selection_changed(self) -> None:
        """Refresh after an account selection changes."""
        self._update_selected_accounts_label()
        self._save_ui_settings()
        self._refresh()

    def _check_all(self) -> None:
        """Select every account for the graph."""
        for variable in self._account_vars.values():
            variable.set(True)
        self._update_selected_accounts_label()
        self._save_ui_settings()
        self._refresh()

    def _uncheck_all(self) -> None:
        """Clear every account selection."""
        for variable in self._account_vars.values():
            variable.set(False)
        self._update_selected_accounts_label()
        self._save_ui_settings()
        self._refresh()

    def _selected_account_ids(self) -> list[int]:
        """Return selected account IDs."""
        return [
            account_id
            for account_id, variable in self._account_vars.items()
            if variable.get()
        ]

    def _update_selected_accounts_label(self) -> None:
        """Update the selected-account count."""
        selected = len(self._selected_account_ids())
        total = len(self._account_vars)
        self.selected_accounts_label.configure(text=f"{selected}/{total}")

    def _refresh(self) -> None:
        """Refresh portfolio history and optional benchmark data."""
        try:
            start_date = date.fromisoformat(self.start_date.get().strip())
            end_date = date.fromisoformat(self.end_date.get().strip())
        except ValueError:
            self.status_label.configure(
                text="Dates must be in YYYY-MM-DD format."
            )
            return

        if start_date > end_date:
            self.status_label.configure(
                text="Start date cannot be after end date."
            )
            return

        self._save_ui_settings()
        account_ids = self._selected_account_ids()
        self._benchmark_previous_value = None

        if not account_ids:
            self._last_history = []
            self._last_benchmark = []
            self._display_history([])
            self._draw_graph([])
            self.status_label.configure(text="No accounts selected.")
            return

        try:
            initialize_database()
            session = get_session()
            try:
                service = PortfolioHistoryService(session)
                # Portfolio History is the consolidated portfolio history.
                # The persisted PortfolioSnapshot with account_id=None is the
                # authoritative portfolio value used by the Portfolio screen.
                # Using individual account snapshots here can produce a
                # different daily change when account snapshots are not
                # perfectly synchronized with the consolidated valuation.
                # Portfolio History is an account-selection graph.  Build the
                # history from the selected account snapshots so deselecting an
                # account changes the graph.  The service carries each selected
                # account's latest known valuation forward to the next valuation
                # date, which also keeps accounts synchronized when their
                # snapshots are recorded on different dates.
                history = service.get_aggregated_history(
                    start_date=start_date,
                    end_date=end_date,
                    account_ids=account_ids,
                )

                # Performance views should only plot actual market trading
                # days. A weekend or market holiday can have a stored
                # portfolio snapshot, but it is not a trading-day
                # performance observation. Use the TSX Composite as the
                # market calendar so statutory/market holidays are handled
                # without maintaining our own holiday list.
                if self.view_mode.get() in {
                    "% Growth Since Start",
                    "Day's Gain/Loss",
                    "% Day's Gain/Loss",
                } and history:
                    trading_days = {
                        point.snapshot_date
                        for point in service.get_benchmark_history(
                            PortfolioHistoryService.BENCHMARKS["TSX Composite"],
                            start_date,
                            end_date,
                        )
                    }
                    history = self._filter_to_trading_days(
                        history,
                        trading_days,
                    )

                benchmark_history = []
                benchmark = self._benchmark_symbol()

                # A benchmark must use the same effective date range as the
                # portfolio data.  The requested period may be much longer
                # than the history we actually have (for example, the user
                # selects 1 Year but only has two days of portfolio data).
                # In that case, do not download a year's worth of benchmark
                # data and compare it to two days of portfolio history.
                if benchmark and history:
                    benchmark_start = max(
                        start_date,
                        history[0].snapshot_date,
                    )
                    benchmark_end = min(
                        end_date,
                        history[-1].snapshot_date,
                    )

                    if benchmark_start <= benchmark_end:
                        benchmark_query_start = benchmark_start
                        if self.view_mode.get() == "% Day's Gain/Loss":
                            # Fetch enough history to obtain the previous
                            # trading-day close.  Daily change must compare
                            # each plotted close with the immediately preceding
                            # trading close, not with the first plotted point.
                            benchmark_query_start = benchmark_start - timedelta(days=14)

                        raw_benchmark_history = service.get_benchmark_history(
                            benchmark,
                            benchmark_query_start,
                            benchmark_end,
                        )

                        if self.view_mode.get() == "% Day's Gain/Loss":
                            prior_points = [
                                point
                                for point in raw_benchmark_history
                                if point.snapshot_date < benchmark_start
                            ]
                            if prior_points:
                                self._benchmark_previous_value = prior_points[-1].value

                            benchmark_history = [
                                point
                                for point in raw_benchmark_history
                                if point.snapshot_date >= benchmark_start
                            ]
                        else:
                            benchmark_history = raw_benchmark_history
            finally:
                session.close()

            self._last_history = history
            self._last_benchmark = benchmark_history

            self._display_history(history)
            self._draw_graph(history)

            benchmark_text = ""
            if benchmark:
                benchmark_text = f"  Benchmark: {benchmark}"

            self.status_label.configure(
                text=(
                    f"{len(history)} valuation(s) found for "
                    f"{len(account_ids)} selected account(s)."
                    f"{benchmark_text}"
                )
            )

        except Exception as exc:
            self.status_label.configure(
                text=f"Error: {type(exc).__name__}: {exc}"
            )

    def _ui_setting_changed(self, *_args) -> None:
        self._save_ui_settings()

    def _restore_ui_settings(self) -> None:
        values = self._ui_settings.get_screen("portfolio_history")
        self._restoring_ui_settings = True
        try:
            if values.get("view") in {
                "Portfolio Value",
                "% Growth Since Start",
                "Day's Gain/Loss",
                "% Day's Gain/Loss",
            }:
                self.view_mode.set(values["view"])
            if values.get("period") in {
                "1 Month", "3 Months", "6 Months", "YTD", "1 Year",
                "3 Years", "5 Years", "All Time", "Custom",
            }:
                self.period.set(values["period"])
            if values.get("benchmark") in {"None", "S&P 500", "TSX Composite", "Custom"}:
                self.benchmark.set(values["benchmark"])
            if isinstance(values.get("custom_benchmark"), str):
                self.custom_benchmark.set(values["custom_benchmark"])
            selected_ids = values.get("selected_account_ids")
            if isinstance(selected_ids, list):
                selected = {
                    int(value) for value in selected_ids
                    if str(value).lstrip("-").isdigit()
                }
                for account_id, variable in self._account_vars.items():
                    variable.set(account_id in selected)

            self._update_benchmark_state()
        except (TypeError, ValueError):
            pass
        finally:
            self._restoring_ui_settings = False

    def _save_ui_settings(self) -> None:
        if self._restoring_ui_settings:
            return
        try:
            self._ui_settings.update(
                "portfolio_history",
                {
                    "view": self.view_mode.get(),
                    "period": self.period.get(),
                    "benchmark": self.benchmark.get(),
                    "custom_benchmark": self.custom_benchmark.get(),
                    "selected_account_ids": [
                        account_id
                        for account_id, variable in self._account_vars.items()
                        if variable.get()
                    ],
                },
            )
        except Exception:
            pass

    def _benchmark_symbol(self) -> str | None:
        """Return the Yahoo symbol for the selected benchmark."""
        benchmark = self.benchmark.get()

        if benchmark == "None":
            return None

        if benchmark == "Custom":
            symbol = self.custom_benchmark.get().strip()
            return symbol or None

        return PortfolioHistoryService.BENCHMARKS.get(benchmark)

    # -------------------------------------------------------------
    # Display
    # -------------------------------------------------------------

    @staticmethod
    def _filter_to_trading_days(
        history: list[PortfolioHistoryPoint],
        trading_days: set[date],
    ) -> list[PortfolioHistoryPoint]:
        """Remove non-trading-day observations from performance history."""
        return [
            point
            for point in history
            if point.snapshot_date.weekday() < 5
            and point.snapshot_date in trading_days
        ]

    def _display_history(
        self,
        history: list[PortfolioHistoryPoint],
    ) -> None:
        """Display the selected history metric in the table."""
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        metric = self.view_mode.get()
        transformed = self._transform_history(history)

        self.history_tree.heading(
            "value",
            text=self._metric_heading(metric),
        )
        self.history_tree.heading(
            "change",
            text="Change",
        )

        for index, point in enumerate(history):
            metric_value = transformed[index]
            change = (
                transformed[index] - transformed[index - 1]
                if index > 0
                else Decimal("0")
            )

            self.history_tree.insert(
                "",
                "end",
                values=(
                    point.snapshot_date.isoformat(),
                    self._format_metric(metric, metric_value),
                    self._format_metric(metric, change),
                ),
            )

    def _transform_history(
        self,
        history: list[PortfolioHistoryPoint],
    ) -> list[Decimal]:
        """Transform stored portfolio valuations into the selected metric."""
        if not history:
            return []

        values = [Decimal(str(point.total_value)) for point in history]
        first = values[0]
        view = self.view_mode.get()

        if view == "Portfolio Value":
            return values

        if view == "% Growth Since Start":
            if first == 0:
                return [Decimal("0") for _ in values]
            return [
                (value - first) / first * Decimal("100")
                for value in values
            ]

        if view == "Day's Gain/Loss":
            return [
                Decimal(str(point.daily_change))
                if point.daily_change is not None
                else Decimal("0")
                for point in history
            ]

        # Day's % Gain/Loss is the stored market-day return for each
        # valuation.  It is deliberately not calculated from the previous
        # graph point because graph points may be sparse and may span cash
        # flows or missed valuation dates.
        return [
            Decimal(str(point.daily_change_percent))
            if point.daily_change_percent is not None
            else Decimal("0")
            for point in history
        ]

    # -------------------------------------------------------------
    # Graph
    # -------------------------------------------------------------

    def _draw_graph(
        self,
        history: list[PortfolioHistoryPoint],
    ) -> None:
        """Draw the selected portfolio metric and optional benchmark."""
        canvas = self.graph_canvas
        canvas.delete("all")

        width = canvas.winfo_width()
        height = canvas.winfo_height()

        if width < 100 or height < 100:
            return

        if not history:
            canvas.create_text(
                width / 2,
                height / 2,
                text="No portfolio valuations for this date range.",
                anchor="center",
            )
            return

        left = 80
        right = 35
        top = 30
        bottom = 55
        graph_width = width - left - right
        graph_height = height - top - bottom

        values = self._transform_history(history)

        # Benchmarks are only available for percentage-based views.
        if self.view_mode.get() == "% Growth Since Start":
            benchmark_values = self._benchmark_growth_values()
        elif self.view_mode.get() == "% Day's Gain/Loss":
            benchmark_values = self._benchmark_daily_change_percent_values()
        else:
            benchmark_values = []

        all_values = list(values)
        if benchmark_values:
            all_values.extend(benchmark_values)

        minimum = min(all_values)
        maximum = max(all_values)

        if minimum == maximum:
            padding = Decimal("1") if minimum == 0 else abs(minimum) * Decimal("0.05")
        else:
            padding = (maximum - minimum) * Decimal("0.10")

        graph_min = minimum - padding
        graph_max = maximum + padding

        if self.view_mode.get() in ("Portfolio Value",):
            graph_min = max(Decimal("0"), graph_min)

        if self.view_mode.get() in {"% Growth Since Start", "% Day's Gain/Loss"}:
            graph_min = min(graph_min, Decimal("0"))
            graph_max = max(graph_max, Decimal("0"))

        if graph_max == graph_min:
            graph_max = graph_min + Decimal("1")

        for i in range(6):
            fraction = i / 5
            y = top + fraction * graph_height
            value = (
                graph_max
                - (graph_max - graph_min) * Decimal(str(fraction))
            )

            canvas.create_line(
                left,
                y,
                width - right,
                y,
                dash=(2, 4),
            )
            canvas.create_text(
                left - 10,
                y,
                text=self._format_axis_value(value),
                anchor="e",
            )

        canvas.create_line(left, top, left, height - bottom)
        canvas.create_line(
            left,
            height - bottom,
            width - right,
            height - bottom,
        )

        if self.view_mode.get() in {"% Growth Since Start", "% Day's Gain/Loss"} and graph_min <= 0 <= graph_max:
            zero_fraction = float((Decimal("0") - graph_min) / (graph_max - graph_min))
            zero_y = top + (1 - zero_fraction) * graph_height
            canvas.create_line(
                left,
                zero_y,
                width - right,
                zero_y,
                fill="green",
                width=2,
            )

        points = self._make_points(
            values,
            history_count=len(history),
            left=left,
            top=top,
            graph_width=graph_width,
            graph_height=graph_height,
            graph_min=graph_min,
            graph_max=graph_max,
        )

        if len(points) >= 2:
            flattened = []
            for x, y in points:
                flattened.extend((x, y))
            canvas.create_line(*flattened, width=2)

        for index, (x, y) in enumerate(points):
            canvas.create_oval(
                x - 3,
                y - 3,
                x + 3,
                y + 3,
                fill="black",
            )

            if index == len(points) - 1:
                canvas.create_text(
                    x,
                    y - 12,
                    text=self._format_axis_value(values[index]),
                    anchor="s",
                )

        if benchmark_values:
            benchmark_points = self._make_benchmark_points(
                benchmark_values,
                left=left,
                top=top,
                graph_width=graph_width,
                graph_height=graph_height,
                graph_min=graph_min,
                graph_max=graph_max,
            )

            if len(benchmark_points) >= 2:
                flattened = []
                for x, y in benchmark_points:
                    flattened.extend((x, y))
                canvas.create_line(
                    *flattened,
                    width=2,
                    dash=(7, 4),
                )

            legend_y = top + 10
            canvas.create_line(
                width - 230,
                legend_y,
                width - 200,
                legend_y,
                width=2,
                dash=(7, 4),
            )
            canvas.create_text(
                width - 195,
                legend_y,
                text=self.benchmark.get(),
                anchor="w",
            )

        label_count = min(6, len(history))
        label_indexes = (
            [0]
            if label_count == 1
            else [
                round(i * (len(history) - 1) / (label_count - 1))
                for i in range(label_count)
            ]
        )

        for index in label_indexes:
            point = history[index]
            if len(history) == 1:
                x = left + graph_width / 2
            else:
                x = left + (
                    index / (len(history) - 1)
                ) * graph_width

            canvas.create_text(
                x,
                height - bottom + 20,
                text=point.snapshot_date.strftime("%Y-%m-%d"),
                anchor="n",
            )

        title = self._metric_heading(self.view_mode.get())
        canvas.create_text(
            left,
            8,
            text=title,
            anchor="w",
            font=("Segoe UI", 10, "bold"),
        )

    def _benchmark_growth_values(self) -> list[Decimal]:
        """Normalize benchmark values to percentage growth."""
        benchmark = getattr(self, "_last_benchmark", [])
        if not benchmark:
            return []

        first = benchmark[0].value
        if first == 0:
            return [Decimal("0") for _ in benchmark]

        return [
            (point.value - first) / first * Decimal("100")
            for point in benchmark
        ]

    def _benchmark_daily_change_percent_values(self) -> list[Decimal]:
        """Return each benchmark trading day's change from its prior close."""
        benchmark = sorted(
            (
                point
                for point in getattr(self, "_last_benchmark", [])
                if point.snapshot_date.weekday() < 5
            ),
            key=lambda point: point.snapshot_date,
        )
        if not benchmark:
            return []

        result: list[Decimal] = []
        previous = getattr(self, "_benchmark_previous_value", None)

        for point in benchmark:
            if previous is None or previous == 0:
                result.append(Decimal("0"))
            else:
                result.append(
                    (point.value - previous)
                    / previous
                    * Decimal("100")
                )
            previous = point.value

        return result

    def _make_benchmark_points(
        self,
        values: list[Decimal],
        *,
        left: float,
        top: float,
        graph_width: float,
        graph_height: float,
        graph_min: Decimal,
        graph_max: Decimal,
    ) -> list[tuple[float, float]]:
        """Map benchmark values to coordinates using their actual dates."""
        benchmark = getattr(self, "_last_benchmark", [])
        if not benchmark or not values:
            return []

        # The benchmark is deliberately plotted against the actual
        # portfolio-history range, not the requested period.  This keeps the
        # benchmark synchronized when the requested period exceeds the amount
        # of portfolio history available.
        history = getattr(self, "_last_history", [])
        if not history:
            return []

        effective_start = history[0].snapshot_date
        effective_end = history[-1].snapshot_date
        day_span = max((effective_end - effective_start).days, 1)

        points = []
        for point, value in zip(benchmark, values):
            x_fraction = (point.snapshot_date - effective_start).days / day_span
            x = left + max(0.0, min(1.0, x_fraction)) * graph_width
            value_fraction = float(
                (value - graph_min) / (graph_max - graph_min)
            )
            y = top + (1 - value_fraction) * graph_height
            points.append((x, y))

        return points

    @staticmethod
    def _make_points(
        values: list[Decimal],
        *,
        history_count: int,
        left: float,
        top: float,
        graph_width: float,
        graph_height: float,
        graph_min: Decimal,
        graph_max: Decimal,
    ) -> list[tuple[float, float]]:
        """Map metric values to canvas coordinates."""
        if not values:
            return []

        points = []
        count = len(values)

        for index, value in enumerate(values):
            x = (
                left + graph_width / 2
                if count == 1
                else left + (index / (count - 1)) * graph_width
            )
            value_fraction = float(
                (value - graph_min) / (graph_max - graph_min)
            )
            y = top + (1 - value_fraction) * graph_height
            points.append((x, y))

        return points

    # -------------------------------------------------------------
    # Formatting
    # -------------------------------------------------------------

    @staticmethod
    def _metric_heading(metric: str) -> str:
        """Return the table/axis heading for a metric."""
        return {
            "Portfolio Value": "Portfolio Value",
            "% Growth Since Start": "% Growth Since Start",
            "Day's Gain/Loss": "Day's Gain/Loss",
            "% Day's Gain/Loss": "% Day's Gain/Loss",
        }.get(metric, metric)

    @staticmethod
    def _format_metric(metric: str, value: Decimal) -> str:
        """Format a metric value."""
        if metric in {"% Growth Since Start", "% Day's Gain/Loss"}:
            return f"{value:+.2f}%"
        return f"${value:+,.2f}" if metric != "Portfolio Value" else f"${value:,.2f}"

    @staticmethod
    def _format_axis_value(value: Decimal) -> str:
        """Format a graph axis value."""
        # Percent is the only non-currency metric.
        # Dollar Value and Day's Gain/Loss are CAD dollar amounts.
        # The graph view can be inferred from the active page via this
        # instance helper's caller; percent is handled below in _draw_graph.
        return f"${value / Decimal('1000000'):,.1f}M" if abs(value) >= Decimal("1000000") else (
            f"${value / Decimal('1000'):,.0f}K"
            if abs(value) >= Decimal("1000")
            else f"${value:,.0f}"
        )

    def _format_axis_value(self, value: Decimal) -> str:
        """Format a graph axis value according to the active metric."""
        if self.view_mode.get() in {"% Growth Since Start", "% Day's Gain/Loss"}:
            return f"{value:+.1f}%"
        return self._format_currency_axis(value)

    @staticmethod
    def _format_currency_axis(value: Decimal) -> str:
        """Format a currency axis value."""
        if abs(value) >= Decimal("1000000"):
            return f"${value / Decimal('1000000'):,.1f}M"
        if abs(value) >= Decimal("1000"):
            return f"${value / Decimal('1000'):,.0f}K"
        return f"${value:,.0f}"

    # -------------------------------------------------------------
    # Resize
    # -------------------------------------------------------------

    def _on_graph_resize(self, _event) -> None:
        """Redraw the graph when the canvas changes size."""
        if self._last_history:
            self._draw_graph(self._last_history)
