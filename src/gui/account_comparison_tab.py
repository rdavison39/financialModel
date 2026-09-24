"""Account comparison graph screen for the Financial Model GUI."""

from __future__ import annotations

import tkinter as tk
from datetime import date, timedelta
from decimal import Decimal
from tkinter import messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from src.database import get_session
from src.database_init import initialize_database
from src.services.portfolio_history_service import PortfolioHistoryService
from src.services.account_comparison_history_service import (
    AccountComparison,
    AccountComparisonHistoryService,
    AccountHistoryPoint,
)
from src.services.ui_settings_service import UISettingsService


class AccountComparisonTab(ttk.Frame):
    """Compare selected account values as separate graph lines."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)

        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

        self._accounts: list[AccountComparison] = []
        self._account_vars: dict[int, tk.BooleanVar] = {}
        self._last_histories: dict[int, list[AccountHistoryPoint]] = {}
        self._last_accounts: dict[int, AccountComparison] = {}
        self._last_benchmark: list = []
        self._benchmark_previous_value: Decimal | None = None
        self._navigation_account_frame: ttk.LabelFrame | None = None
        self._ui_settings = UISettingsService()
        self._restoring_ui_settings = False

        self._build_ui()
        self._update_benchmark_state()
        self._build_navigation_account_selector()
        for variable in (
            self.view_var,
            self.period_var,
            self.benchmark_var,
            self.custom_benchmark_var,
            self.start_var,
            self.end_var,
        ):
            variable.trace_add("write", self._ui_setting_changed)
        self._load_accounts()

        self.bind("<Map>", self._show_navigation_account_selector, add="+")
        self.bind("<Unmap>", self._hide_navigation_account_selector, add="+")
        self.winfo_toplevel().bind(
            "<<PortfolioUpdated>>",
            self._on_portfolio_updated,
            add="+",
        )
        self.winfo_toplevel().bind(
            "<Configure>",
            self._on_window_configure,
            add="+",
        )

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Build the Account History page using the Portfolio History layout."""
        ttk.Label(
            self,
            text="Account History",
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
            row=0,
            column=0,
            padx=(0, 5),
        )

        self.view_var = tk.StringVar(value="Portfolio Value")
        view_combo = ttk.Combobox(
            controls,
            textvariable=self.view_var,
            values=(
                "Portfolio Value",
                "% Growth Since Start",
                "Day's Gain/Loss",
                "% Day's Gain/Loss",
            ),
            state="readonly",
            width=15,
        )
        view_combo.grid(row=0, column=1, padx=(0, 12))
        view_combo.bind("<<ComboboxSelected>>", self._view_changed)

        # Period
        ttk.Label(controls, text="Period:").grid(
            row=0,
            column=2,
            padx=(0, 5),
        )

        self.period_var = tk.StringVar(value="1 Year")
        period_combo = ttk.Combobox(
            controls,
            textvariable=self.period_var,
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
            row=0,
            column=4,
            padx=(0, 5),
        )

        self.benchmark_var = tk.StringVar(value="TSX Composite")
        self.benchmark_combo = ttk.Combobox(
            controls,
            textvariable=self.benchmark_var,
            values=(
                "None",
                "S&P 500",
                "TSX Composite",
                "Custom",
            ),
            state="readonly",
            width=14,
        )
        self.benchmark_combo.grid(row=0, column=5, padx=(0, 5))
        self.benchmark_combo.bind(
            "<<ComboboxSelected>>",
            self._benchmark_changed,
        )

        self.custom_benchmark_var = tk.StringVar(value="")
        self.custom_benchmark_entry = ttk.Entry(
            controls,
            textvariable=self.custom_benchmark_var,
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
            lambda _event: self._refresh_chart(),
        )

        # Dates
        ttk.Label(controls, text="Start:").grid(
            row=1,
            column=0,
            padx=(0, 5),
            pady=(8, 0),
        )

        self.start_var = tk.StringVar(
            value=(date.today() - timedelta(days=365)).isoformat()
        )
        ttk.Entry(
            controls,
            textvariable=self.start_var,
            width=12,
        ).grid(
            row=1,
            column=1,
            padx=(0, 12),
            pady=(8, 0),
        )

        ttk.Label(controls, text="End:").grid(
            row=1,
            column=2,
            padx=(0, 5),
            pady=(8, 0),
        )

        self.end_var = tk.StringVar(value=date.today().isoformat())
        ttk.Entry(
            controls,
            textvariable=self.end_var,
            width=12,
        ).grid(
            row=1,
            column=3,
            padx=(0, 12),
            pady=(8, 0),
        )

        ttk.Button(
            controls,
            text="Refresh",
            command=self._refresh_chart,
        ).grid(
            row=1,
            column=4,
            columnspan=3,
            pady=(8, 0),
            sticky="w",
        )

        main = ttk.Frame(self)
        main.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="nsew",
        )
        main.columnconfigure(0, weight=1)
        main.rowconfigure(0, weight=1)

        chart_frame = ttk.LabelFrame(
            main,
            text="Account Values",
            padding=8,
        )
        chart_frame.grid(
            row=0,
            column=0,
            sticky="nsew",
            pady=(0, 8),
        )
        chart_frame.columnconfigure(0, weight=1)
        chart_frame.rowconfigure(0, weight=1)

        self.figure = Figure(figsize=(10, 6), dpi=100)
        self.axis = self.figure.add_subplot(111)

        self.chart_canvas = FigureCanvasTkAgg(
            self.figure,
            master=chart_frame,
        )
        self.chart_canvas.get_tk_widget().grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        history_frame = ttk.LabelFrame(
            main,
            text="Latest Values",
            padding=5,
        )
        history_frame.grid(
            row=1,
            column=0,
            sticky="nsew",
        )
        main.rowconfigure(0, weight=3)
        main.rowconfigure(1, weight=1)
        history_frame.columnconfigure(0, weight=1)
        history_frame.rowconfigure(0, weight=1)

        self.history_tree = ttk.Treeview(
            history_frame,
            columns=("account", "date", "value"),
            show="headings",
            height=6,
        )
        self.history_tree.heading("account", text="Account")
        self.history_tree.heading("date", text="Date")
        self.history_tree.heading("value", text="Value")
        self.history_tree.column(
            "account",
            width=400,
            minwidth=180,
            stretch=True,
        )
        self.history_tree.column(
            "date",
            width=110,
            minwidth=100,
            stretch=False,
        )
        self.history_tree.column(
            "value",
            width=180,
            minwidth=150,
            anchor="e",
            stretch=False,
        )
        self.history_tree.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        history_scroll = ttk.Scrollbar(
            history_frame,
            orient="vertical",
            command=self.history_tree.yview,
        )
        history_scroll.grid(row=0, column=1, sticky="ns")
        self.history_tree.configure(yscrollcommand=history_scroll.set)

        self.status_label = ttk.Label(
            self,
            text="Select accounts to view account history.",
        )
        self.status_label.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(6, 0),
        )

        self._set_period_dates("1 Year")

    # ------------------------------------------------------------------
    # Navigation account selector
    # ------------------------------------------------------------------

    def _build_navigation_account_selector(self) -> None:
        """Create the account checklist below the left navigation buttons."""
        navigation = self._find_navigation_frame()
        if navigation is None:
            return

        frame_background = (
            ttk.Style().lookup("TFrame", "background") or "white"
        )

        self._navigation_account_frame = ttk.LabelFrame(
            navigation,
            text="Accounts to Graph",
            width=235,
            height=500,
            padding=5,
        )
        self._navigation_account_frame.pack(
            fill="x",
            pady=(10, 0),
        )
        self._navigation_account_frame.pack_propagate(False)

        controls = ttk.Frame(self._navigation_account_frame)
        controls.pack(fill="x", pady=(0, 4))

        ttk.Button(
            controls,
            text="All",
            command=self._select_all,
            width=5,
        ).pack(side="left")
        ttk.Button(
            controls,
            text="None",
            command=self._select_none,
            width=6,
        ).pack(side="left", padx=(4, 0))

        self.count_label = ttk.Label(controls, text="0/0")
        self.count_label.pack(side="right")

        list_frame = ttk.Frame(self._navigation_account_frame)
        list_frame.pack(fill="both", expand=True)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.account_canvas = tk.Canvas(
            list_frame,
            highlightthickness=0,
            background=frame_background,
            width=215,
        )
        self.account_canvas.grid(row=0, column=0, sticky="nsew")

        self.account_inner = ttk.Frame(self.account_canvas)
        self.account_window = self.account_canvas.create_window(
            0,
            0,
            window=self.account_inner,
            anchor="nw",
        )

        self.account_scrollbar = ttk.Scrollbar(
            list_frame,
            orient="vertical",
            command=self.account_canvas.yview,
        )
        self.account_scrollbar.grid(row=0, column=1, sticky="ns")

        self.account_hscrollbar = ttk.Scrollbar(
            list_frame,
            orient="horizontal",
            command=self.account_canvas.xview,
        )
        self.account_hscrollbar.grid(row=1, column=0, sticky="ew")

        self.account_canvas.configure(
            yscrollcommand=self.account_scrollbar.set,
            xscrollcommand=self.account_hscrollbar.set,
        )
        self.account_inner.bind(
            "<Configure>",
            self._update_account_scrollregion,
        )
        self.account_canvas.bind(
            "<Configure>",
            self._resize_account_inner,
        )
        self._navigation_account_frame.pack_forget()

    def _find_navigation_frame(self) -> ttk.Frame | None:
        """Return the application's shared navigation frame.

        The main application exposes this frame directly.  Using that
        reference is important because navigation button labels are user-
        facing and may change without breaking the account selector.
        """
        navigation = getattr(self.winfo_toplevel(), "navigation", None)
        if isinstance(navigation, ttk.Frame):
            return navigation
        return None

    def _show_navigation_account_selector(self, _event=None) -> None:
        if self._navigation_account_frame is not None:
            self._navigation_account_frame.pack(fill="x", pady=(10, 0))
            self.after_idle(self._sync_navigation_account_height)

    def _hide_navigation_account_selector(self, _event=None) -> None:
        if self._navigation_account_frame is not None:
            self._navigation_account_frame.pack_forget()

    def _on_window_configure(self, _event=None) -> None:
        if self.winfo_ismapped():
            self.after_idle(self._sync_navigation_account_height)

    def _sync_navigation_account_height(self) -> None:
        """Keep the account selector approximately aligned with the main content."""
        frame = self._navigation_account_frame
        if frame is None or not frame.winfo_ismapped():
            return

        self.update_idletasks()
        main_bottom = self.winfo_rooty() + self.winfo_height()
        frame_top = frame.winfo_rooty()
        desired_height = main_bottom - frame_top - 4
        if desired_height > 100:
            frame.configure(height=desired_height)

    def _update_account_scrollregion(self, _event=None) -> None:
        self.account_canvas.configure(
            scrollregion=self.account_canvas.bbox("all")
        )

    def _resize_account_inner(self, event) -> None:
        requested_width = self.account_inner.winfo_reqwidth()
        self.account_canvas.itemconfigure(
            self.account_window,
            width=max(requested_width, event.width),
        )

    # ------------------------------------------------------------------
    # Accounts
    # ------------------------------------------------------------------

    def _load_accounts(self) -> None:
        """Load account checkboxes from the database."""
        try:
            initialize_database()
            session = get_session()
            try:
                accounts = AccountComparisonHistoryService(
                    session
                ).get_accounts()
            finally:
                session.close()

            self._accounts = accounts
            self._last_accounts = {
                account.account_id: account for account in accounts
            }

            for widget in self.account_inner.winfo_children():
                widget.destroy()

            self._account_vars.clear()

            # Match Portfolio History: all accounts are selected initially.
            for row, account in enumerate(accounts):
                variable = tk.BooleanVar(value=True)
                self._account_vars[account.account_id] = variable

                ttk.Checkbutton(
                    self.account_inner,
                    text=account.label,
                    variable=variable,
                    command=self._selection_changed,
                ).grid(
                    row=row,
                    column=0,
                    sticky="w",
                    padx=0,
                    pady=1,
                )

            self._update_account_count()
            self._restore_ui_settings()
            self._update_account_count()
            self._update_account_scrollregion()
            self._refresh_chart()

        except Exception as exc:
            self.status_label.configure(
                text=f"Unable to load accounts: {type(exc).__name__}"
            )

    def _selection_changed(self) -> None:
        self._update_account_count()
        self._save_ui_settings()
        self._refresh_chart()

    def _update_account_count(self) -> None:
        selected = sum(
            variable.get()
            for variable in self._account_vars.values()
        )
        self.count_label.configure(
            text=f"{selected}/{len(self._accounts)}"
        )

    def _select_all(self) -> None:
        for variable in self._account_vars.values():
            variable.set(True)
        self._update_account_count()
        self._save_ui_settings()
        self._refresh_chart()

    def _select_none(self) -> None:
        for variable in self._account_vars.values():
            variable.set(False)
        self._update_account_count()
        self._save_ui_settings()
        self._clear_chart()

    def _selected_ids(self) -> list[int]:
        return [
            account_id
            for account_id, variable in self._account_vars.items()
            if variable.get()
        ]

    # ------------------------------------------------------------------
    # Period / controls
    # ------------------------------------------------------------------

    def _period_changed(self, _event=None) -> None:
        period = self.period_var.get()
        if period != "Custom":
            self._set_period_dates(period)
        self._save_ui_settings()
        self._refresh_chart()

    def _set_period_dates(self, period: str) -> None:
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

        self.start_var.set(start.isoformat())
        self.end_var.set(end.isoformat())

    def _view_changed(self, _event=None) -> None:
        """Refresh after changing the history metric."""
        self._update_benchmark_state()
        self._refresh_chart()

    def _benchmark_changed(self, _event=None) -> None:
        """Refresh after changing the benchmark."""
        if not self._benchmark_is_supported():
            self.benchmark_var.set("None")

        if (
            self.benchmark_var.get() == "Custom"
            and self._benchmark_is_supported()
        ):
            self.custom_benchmark_entry.grid()
        else:
            self.custom_benchmark_entry.grid_remove()

        self._save_ui_settings()
        self._refresh_chart()

    def _benchmark_is_supported(self) -> bool:
        """Return whether the current view supports benchmark comparison."""
        return self.view_var.get() in {
            "% Growth Since Start",
            "% Day's Gain/Loss",
        }

    def _update_benchmark_state(self) -> None:
        """Enable benchmarks only for percentage-based views."""
        if self._benchmark_is_supported():
            self.benchmark_combo.configure(state="readonly")
            if self.benchmark_var.get() == "Custom" and self.custom_benchmark_var.get().strip():
                self.custom_benchmark_entry.grid()
            else:
                self.custom_benchmark_entry.grid_remove()
        else:
            self.benchmark_var.set("None")
            self.benchmark_combo.configure(state="disabled")
            self.custom_benchmark_entry.grid_remove()

    def _ui_setting_changed(self, *_args) -> None:
        self._save_ui_settings()

    def _restore_ui_settings(self) -> None:
        values = self._ui_settings.get_screen("account_history")
        self._restoring_ui_settings = True
        try:
            if values.get("view") in {
                "Portfolio Value",
                "% Growth Since Start",
                "Day's Gain/Loss",
                "% Day's Gain/Loss",
            }:
                self.view_var.set(values["view"])
            if values.get("period") in {
                "1 Month", "3 Months", "6 Months", "YTD", "1 Year",
                "3 Years", "5 Years", "All Time", "Custom",
            }:
                self.period_var.set(values["period"])
            if values.get("benchmark") in {
                "None", "S&P 500", "TSX Composite", "Custom"
            }:
                self.benchmark_var.set(values["benchmark"])
            if isinstance(values.get("custom_benchmark"), str):
                self.custom_benchmark_var.set(values["custom_benchmark"])
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
                "account_history",
                {
                    "view": self.view_var.get(),
                    "period": self.period_var.get(),
                    "benchmark": self.benchmark_var.get(),
                    "custom_benchmark": self.custom_benchmark_var.get(),
                    "selected_account_ids": [
                        account_id
                        for account_id, variable in self._account_vars.items()
                        if variable.get()
                    ],
                },
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Data / graph
    # ------------------------------------------------------------------

    def _parse_dates(self) -> tuple[date, date] | None:
        try:
            start = date.fromisoformat(self.start_var.get().strip())
            end = date.fromisoformat(self.end_var.get().strip())
        except ValueError:
            messagebox.showerror(
                "Account History",
                "Dates must use YYYY-MM-DD.",
            )
            return None

        if start > end:
            messagebox.showerror(
                "Account History",
                "Start Date must be on or before End Date.",
            )
            return None

        return start, end

    def _refresh_chart(self) -> None:
        self._save_ui_settings()
        parsed = self._parse_dates()
        if parsed is None:
            return

        selected_ids = self._selected_ids()
        if not selected_ids:
            self._clear_chart()
            self.status_label.configure(text="No accounts selected.")
            return

        start, end = parsed
        self._benchmark_previous_value = None

        try:
            initialize_database()
            session = get_session()
            try:
                service = AccountComparisonHistoryService(session)
                histories = service.get_histories(
                    selected_ids,
                    start,
                    end,
                )

                # Performance views should only plot actual market trading
                # days. A weekend or market holiday can have a stored
                # account snapshot, but it is not a trading-day performance
                # observation. Use the TSX Composite as the market calendar
                # so statutory/market holidays are handled without
                # maintaining our own holiday list.
                if self.view_var.get() in {
                    "% Growth Since Start",
                    "Day's Gain/Loss",
                    "% Day's Gain/Loss",
                }:
                    trading_days = {
                        point.snapshot_date
                        for point in PortfolioHistoryService(session).get_benchmark_history(
                            PortfolioHistoryService.BENCHMARKS["TSX Composite"],
                            start,
                            end,
                        )
                    }
                    histories = self._filter_to_trading_days(
                        histories,
                        trading_days,
                    )

                benchmark_history = []
                benchmark = self._benchmark_symbol()

                # The benchmark must use the actual available account-history
                # range, not the requested period.  This keeps a 1-year
                # benchmark from appearing when the selected accounts only
                # contain a few days of valuation history.
                if benchmark and histories:
                    available_ranges = [
                        (points[0].snapshot_date, points[-1].snapshot_date)
                        for points in histories.values()
                        if points
                    ]
                    if available_ranges:
                        benchmark_start = max(
                            start,
                            min(first for first, _last in available_ranges),
                        )
                        benchmark_end = min(
                            end,
                            max(last for _first, last in available_ranges),
                        )

                        if benchmark_start <= benchmark_end:
                            benchmark_query_start = benchmark_start
                            if self.view_var.get() == "% Day's Gain/Loss":
                                benchmark_query_start = benchmark_start - timedelta(days=14)

                            raw_benchmark_history = (
                                PortfolioHistoryService(session).get_benchmark_history(
                                    benchmark,
                                    benchmark_query_start,
                                    benchmark_end,
                                )
                            )
                            raw_benchmark_history = [
                                point
                                for point in raw_benchmark_history
                                if point.snapshot_date.weekday() < 5
                            ]

                            if self.view_var.get() == "% Day's Gain/Loss":
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

            self._last_histories = histories
            self._last_benchmark = benchmark_history
            self._redraw()

        except Exception as exc:
            messagebox.showerror(
                "Account History",
                "Unable to load history:\n\n"
                f"{type(exc).__name__}: {exc}",
            )

    def _benchmark_symbol(self) -> str | None:
        benchmark = self.benchmark_var.get()
        if benchmark == "None":
            return None
        if benchmark == "Custom":
            symbol = self.custom_benchmark_var.get().strip()
            return symbol or None
        return PortfolioHistoryService.BENCHMARKS.get(benchmark)

    def _benchmark_growth_values(self) -> list[Decimal]:
        """Return benchmark growth from the first plotted close."""
        if not self._last_benchmark:
            return []

        first = self._last_benchmark[0].value
        if first == 0:
            return [Decimal("0") for _ in self._last_benchmark]

        return [
            (point.value - first) / first * Decimal("100")
            for point in self._last_benchmark
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

    @staticmethod
    def _filter_to_trading_days(
        histories: dict[int, list[AccountHistoryPoint]],
        trading_days: set[date],
    ) -> dict[int, list[AccountHistoryPoint]]:
        """Remove non-trading-day observations from performance histories."""
        return {
            account_id: [
                point
                for point in points
                if point.snapshot_date.weekday() < 5
                and point.snapshot_date in trading_days
            ]
            for account_id, points in histories.items()
        }

    @staticmethod
    def _transform_account_history(
        points: list[AccountHistoryPoint],
        view: str,
    ) -> list[Decimal]:
        """Transform account snapshots into one of the four history views."""
        if not points:
            return []

        values = [Decimal(str(point.total_value)) for point in points]
        first = values[0]

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
                for point in points
            ]

        return [
            Decimal(str(point.daily_change_percent))
            if point.daily_change_percent is not None
            else Decimal("0")
            for point in points
        ]

    def _redraw(self) -> None:
        self.axis.clear()

        selected_ids = self._selected_ids()
        plotted = 0
        view = self.view_var.get()
        percent_mode = view in {
            "% Growth Since Start",
            "% Day's Gain/Loss",
        }

        for account_id in selected_ids:
            points = self._last_histories.get(account_id, [])
            if not points:
                continue

            account = self._last_accounts.get(account_id)
            if account is None:
                continue

            dates = [point.snapshot_date for point in points]
            metric_values = self._transform_account_history(points, view)
            values = [float(value) for value in metric_values]

            self.axis.plot(
                dates,
                values,
                marker="o",
                linewidth=1.8,
                markersize=4,
                label=account.label,
            )
            plotted += 1

        if view == "% Growth Since Start":
            benchmark_values = self._benchmark_growth_values()
        elif view == "% Day's Gain/Loss":
            benchmark_values = self._benchmark_daily_change_percent_values()
        else:
            benchmark_values = []

        if benchmark_values:
            benchmark_dates = [
                point.snapshot_date for point in self._last_benchmark
            ]
            self.axis.plot(
                benchmark_dates,
                [float(value) for value in benchmark_values],
                linestyle="--",
                linewidth=1.5,
                label=self.benchmark_var.get(),
            )
            plotted += 1

        if percent_mode:
            self.axis.set_ylabel(
                "% Growth Since Start"
                if view == "% Growth Since Start"
                else "% Day's Gain/Loss"
            )
            self.axis.axhline(0, linewidth=0.8, linestyle="--")
            self.axis.yaxis.set_major_formatter(
                lambda value, _position: f"{value:+.1f}%"
            )
        elif view == "Day's Gain/Loss":
            self.axis.set_ylabel("Day's Gain/Loss (CAD)")
            self.axis.axhline(0, linewidth=0.8, linestyle="--")
            self.axis.yaxis.set_major_formatter(
                lambda value, _position: (
                    f"${value / 1_000_000:+.1f}M"
                    if abs(value) >= 1_000_000
                    else f"${value / 1_000:+.0f}K"
                )
            )
        else:
            self.axis.set_ylabel("Account Value (CAD)")
            self.axis.yaxis.set_major_formatter(
                lambda value, _position: (
                    f"${value / 1_000_000:.1f}M"
                    if abs(value) >= 1_000_000
                    else f"${value / 1_000:.0f}K"
                )
            )

        self.axis.set_xlabel("Date")
        self.axis.grid(True, axis="y", linestyle=":", linewidth=0.8)

        if plotted:
            self.axis.legend(
                loc="upper left",
                bbox_to_anchor=(1.01, 1),
                borderaxespad=0,
                fontsize=8,
            )
            self.figure.tight_layout()
            self.chart_canvas.draw_idle()

            self.status_label.configure(
                text=(
                    f"{plotted} series plotted. "
                    f"{self._view_status_text(view)}."
                )
            )
        else:
            self.axis.text(
                0.5,
                0.5,
                "No historical valuation data for the selected accounts.",
                ha="center",
                va="center",
                transform=self.axis.transAxes,
            )
            self.chart_canvas.draw_idle()
            self.status_label.configure(
                text="No historical valuation data for the selected accounts."
            )

        self._populate_latest_values(selected_ids)

    @staticmethod
    def _view_status_text(view: str) -> str:
        return {
            "Portfolio Value": "Portfolio value view",
            "% Growth Since Start": "Growth since start view",
            "Day's Gain/Loss": "Day's gain/loss view",
            "% Day's Gain/Loss": "Day's percentage gain/loss view",
        }.get(view, view)

    def _populate_latest_values(self, selected_ids: list[int]) -> None:
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        for account_id in selected_ids:
            points = self._last_histories.get(account_id, [])
            account = self._last_accounts.get(account_id)

            if not points or account is None:
                continue

            latest = points[-1]
            view = self.view_var.get()
            if view == "Portfolio Value":
                display_value = f"${latest.total_value:,.2f}"
            elif view == "% Growth Since Start":
                base = points[0].total_value
                growth = (
                    (latest.total_value - base) / base * Decimal("100")
                    if base != 0
                    else Decimal("0")
                )
                display_value = f"{growth:+.2f}%"
            elif view == "Day's Gain/Loss":
                display_value = f"${latest.daily_change or Decimal('0'):+,.2f}"
            else:
                display_value = f"{latest.daily_change_percent or Decimal('0'):+.2f}%"

            self.history_tree.insert(
                "",
                "end",
                values=(
                    account.label,
                    latest.snapshot_date.isoformat(),
                    display_value,
                ),
            )

    def _clear_chart(self) -> None:
        self._last_histories = {}
        self._last_benchmark = []
        self.axis.clear()
        self.axis.set_xlabel("Date")
        self.axis.set_ylabel("Account Value (CAD)")
        self.chart_canvas.draw_idle()

        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

    def _on_portfolio_updated(self, _event=None) -> None:
        """Reload current account list after a portfolio update."""
        self._load_accounts()


def main() -> None:
    """Run the account comparison screen standalone."""
    root = tk.Tk()
    root.title("Financial Model - Account History")
    root.geometry("1550x900")
    root.minsize(1200, 700)

    AccountComparisonTab(root).pack(
        fill="both",
        expand=True,
        padx=15,
        pady=15,
    )

    root.mainloop()


if __name__ == "__main__":
    main()
