"""Holdings history screen for the Financial Model GUI."""

from __future__ import annotations

import tkinter as tk
from datetime import date, datetime, timedelta
from tkinter import messagebox, ttk

from sqlalchemy import select

from src.database import get_session
from src.database_init import initialize_database
from src.services.portfolio_comparison_service import PortfolioComparisonService
from src.services.ui_settings_service import UISettingsService


class ComparisonTab(ttk.Frame):
    """Show how selected holdings changed between two dates."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(4, weight=1)

        self._accounts = []
        self._account_vars: dict[int, tk.BooleanVar] = {}
        self._navigation_account_frame: ttk.LabelFrame | None = None
        self._ui_settings = UISettingsService()
        self._restoring_ui_settings = False

        self._build_ui()
        self._build_navigation_account_selector()
        for variable in (self.from_var, self.to_var):
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
        ttk.Label(
            self,
            text="Holdings History",
            font=("Segoe UI", 18, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 15))

        controls = ttk.Frame(self)
        controls.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        ttk.Label(controls, text="From:").pack(side="left")
        self.from_var = tk.StringVar(
            value=(date.today() - timedelta(days=365)).isoformat()
        )
        ttk.Entry(
            controls,
            textvariable=self.from_var,
            width=12,
        ).pack(side="left", padx=(5, 14))

        ttk.Label(controls, text="To:").pack(side="left")
        self.to_var = tk.StringVar(value=date.today().isoformat())
        ttk.Entry(
            controls,
            textvariable=self.to_var,
            width=12,
        ).pack(side="left", padx=(5, 8))

        ttk.Button(
            controls,
            text="Refresh",
            command=self._compare,
        ).pack(side="left", padx=4)

        self.heading = ttk.Label(
            self,
            text="Consolidated Portfolio",
            font=("Segoe UI", 13, "bold"),
        )
        self.heading.grid(row=2, column=0, sticky="w", pady=(0, 8))

        summary = ttk.Frame(self)
        summary.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        self.from_value = self._summary(summary, "From Value:", 0)
        self.to_value = self._summary(summary, "To Value:", 2)
        self.change = self._summary(summary, "Change:", 4)
        self.count = ttk.Label(summary, text="Holdings: --")
        self.count.grid(row=0, column=6, padx=20)

        frame = ttk.Frame(self)
        frame.grid(row=4, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        cols = (
            "symbol", "company", "q1", "q2", "dq",
            "a1", "a2", "mv1", "mv2", "g1", "g2", "status",
        )
        self.tree = ttk.Treeview(frame, columns=cols, show="headings")
        heads = {
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
        widths = [100, 220, 90, 90, 100, 115, 115, 140, 140, 145, 145, 100]
        for column, width in zip(cols, widths):
            self.tree.heading(column, text=heads[column])
            self.tree.column(
                column,
                width=width,
                minwidth=70,
                stretch=False,
                anchor="w" if column in ("symbol", "company", "status") else "e",
            )
        self.tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(
            frame,
            orient="vertical",
            command=self.tree.yview,
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.tag_configure("increase", foreground="green")
        self.tree.tag_configure("decrease", foreground="red")
        self.tree.tag_configure("neutral", foreground="black")

        self.status = ttk.Label(self, text="Select accounts and a date range.")
        self.status.grid(row=5, column=0, sticky="w", pady=(8, 0))

    @staticmethod
    def _summary(parent, label, column):
        ttk.Label(
            parent,
            text=label,
            font=("Segoe UI", 10, "bold"),
        ).grid(row=0, column=column, sticky="e")
        value = ttk.Label(parent, text="--")
        value.grid(row=0, column=column + 1, sticky="w", padx=(5, 0))
        return value

    # ------------------------------------------------------------------
    # Navigation account selector
    # ------------------------------------------------------------------

    def _build_navigation_account_selector(self) -> None:
        """Create the account checklist below the left navigation buttons."""
        navigation = self._find_navigation_frame()
        if navigation is None:
            return

        background = ttk.Style().lookup("TFrame", "background") or "white"

        self._navigation_account_frame = ttk.LabelFrame(
            navigation,
            text="Accounts to Compare",
            width=235,
            height=500,
            padding=5,
        )
        self._navigation_account_frame.pack(fill="x", pady=(10, 0))
        self._navigation_account_frame.pack_propagate(False)

        controls = ttk.Frame(self._navigation_account_frame)
        controls.pack(fill="x", pady=(0, 4))

        ttk.Button(
            controls,
            text="All",
            width=5,
            command=self._select_all,
        ).pack(side="left")
        ttk.Button(
            controls,
            text="None",
            width=6,
            command=self._select_none,
        ).pack(side="left", padx=(4, 0))

        self.selected_accounts_label = ttk.Label(controls, text="0/0")
        self.selected_accounts_label.pack(side="right")

        list_frame = ttk.Frame(self._navigation_account_frame)
        list_frame.pack(fill="both", expand=True)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.account_canvas = tk.Canvas(
            list_frame,
            highlightthickness=0,
            background=background,
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
        self.account_inner.bind("<Configure>", self._update_account_scrollregion)
        self.account_canvas.bind("<Configure>", self._resize_account_inner)

        self._navigation_account_frame.pack_forget()

    def _find_navigation_frame(self) -> ttk.Frame | None:
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
        session = None
        try:
            initialize_database()
            session = get_session()
            self._accounts = PortfolioComparisonService(session).get_accounts()

            for widget in self.account_inner.winfo_children():
                widget.destroy()
            self._account_vars.clear()

            # Match Portfolio History: all accounts are selected initially.
            for row, account in enumerate(self._accounts):
                variable = tk.BooleanVar(value=True)
                self._account_vars[account.account_id] = variable

                ttk.Checkbutton(
                    self.account_inner,
                    text=(
                        f"{account.brokerage_name} - {account.account_number}"
                        + (f" - {account.account_name}" if account.account_name else "")
                    ),
                    variable=variable,
                    command=self._selection_changed,
                ).grid(row=row, column=0, sticky="w", padx=0, pady=1)

            self._update_account_count()
            self._update_account_scrollregion()

            today = date.today()
            self.from_var.set(self._fmt_date(today - timedelta(days=365)))
            self.to_var.set(self._fmt_date(today))

            self._restore_ui_settings()
            self._update_account_count()
            self._compare()
        except Exception as exc:
            self.status.configure(
                text=f"Unable to load accounts: {type(exc).__name__}: {exc}"
            )
        finally:
            if session is not None:
                session.close()

    def _selection_changed(self) -> None:
        self._update_account_count()
        self._save_ui_settings()
        self._compare()

    def _update_account_count(self) -> None:
        selected = sum(
            variable.get() for variable in self._account_vars.values()
        )
        self.selected_accounts_label.configure(
            text=f"{selected}/{len(self._accounts)}"
        )

    def _select_all(self) -> None:
        for variable in self._account_vars.values():
            variable.set(True)
        self._update_account_count()
        self._save_ui_settings()
        self._compare()

    def _select_none(self) -> None:
        for variable in self._account_vars.values():
            variable.set(False)
        self._update_account_count()
        self._save_ui_settings()
        self._clear_results()

    def _ui_setting_changed(self, *_args) -> None:
        self._save_ui_settings()

    def _restore_ui_settings(self) -> None:
        values = self._ui_settings.get_screen("holdings_history")
        self._restoring_ui_settings = True
        try:
            selected_ids = values.get("selected_account_ids")
            if isinstance(selected_ids, list):
                selected = {
                    int(value) for value in selected_ids
                    if str(value).lstrip("-").isdigit()
                }
                for account_id, variable in self._account_vars.items():
                    variable.set(account_id in selected)
        except (TypeError, ValueError):
            pass
        finally:
            self._restoring_ui_settings = False

    def _save_ui_settings(self) -> None:
        if self._restoring_ui_settings:
            return
        try:
            self._ui_settings.update(
                "holdings_history",
                {
                    "selected_account_ids": [
                        account_id
                        for account_id, variable in self._account_vars.items()
                        if variable.get()
                    ],
                },
            )
        except Exception:
            pass

    def _selected_ids(self) -> list[int]:
        return [
            account_id
            for account_id, variable in self._account_vars.items()
            if variable.get()
        ]

    # ------------------------------------------------------------------
    # Comparison
    # ------------------------------------------------------------------

    def _compare(self) -> None:
        self._save_ui_settings()
        selected_ids = self._selected_ids()
        if not selected_ids:
            self._clear_results()
            return

        try:
            first_date = self._date(self.from_var.get())
            second_date = self._date(self.to_var.get())
        except ValueError:
            messagebox.showwarning(
                "Holdings History",
                "Enter dates using YYYY-MM-DD.",
            )
            return

        if first_date > second_date:
            messagebox.showwarning(
                "Holdings History",
                "From date must be on or before To date.",
            )
            return

        session = None
        try:
            initialize_database()
            session = get_session()
            result = PortfolioComparisonService(session).compare(
                first_date,
                second_date,
                account_ids=selected_ids,
            )
        except Exception as exc:
            messagebox.showerror(
                "Holdings History",
                f"Unable to compare holdings:\n\n{type(exc).__name__}: {exc}",
            )
            return
        finally:
            if session is not None:
                session.close()

        self._display(result, first_date, second_date, len(selected_ids))

    def _display(self, result, first_date, second_date, selected_count: int) -> None:
        if selected_count == len(self._accounts):
            heading = "Consolidated Portfolio"
        elif selected_count == 1:
            selected_id = self._selected_ids()[0]
            account = next(
                account for account in self._accounts
                if account.account_id == selected_id
            )
            heading = (
                f"{account.brokerage_name} - {account.account_number}"
                + (f" - {account.account_name}" if account.account_name else "")
            )
        else:
            heading = f"Selected Accounts ({selected_count})"

        self.heading.configure(text=heading)
        self.from_value.configure(text=self._money(result.first_value))
        self.to_value.configure(text=self._money(result.second_value))
        self.change.configure(text=self._smoney(result.value_difference))

        active = [
            position
            for position in result.positions
            if position.first_quantity != 0 or position.second_quantity != 0
        ]
        self.count.configure(text=f"Holdings: {len(active)}")

        for item in self.tree.get_children():
            self.tree.delete(item)

        for position in result.positions:
            tag = (
                "increase"
                if position.quantity_difference > 0
                else "decrease"
                if position.quantity_difference < 0
                else "neutral"
            )
            self.tree.insert(
                "",
                "end",
                values=(
                    position.symbol,
                    position.company_name,
                    self._qty(position.first_quantity),
                    self._qty(position.second_quantity),
                    self._sq(position.quantity_difference),
                    self._money(position.first_average_cost),
                    self._money(position.second_average_cost),
                    self._money(position.first_market_value),
                    self._money(position.second_market_value),
                    self._smoney(position.first_unrealized_gain),
                    self._smoney(position.second_unrealized_gain),
                    position.status,
                ),
                tags=(tag,),
            )

        self.status.configure(
            text=(
                f"{first_date:%Y-%m-%d} → {second_date:%Y-%m-%d}   "
                f"{len(active)} active holdings across {selected_count} account(s)"
            )
        )

    def _clear_results(self) -> None:
        self.heading.configure(text="No Accounts Selected")
        self.from_value.configure(text="--")
        self.to_value.configure(text="--")
        self.change.configure(text="--")
        self.count.configure(text="Holdings: --")
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.status.configure(text="Select one or more accounts.")

    def _on_portfolio_updated(self, _event=None) -> None:
        self._load_accounts()

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    @staticmethod
    def _fmt_date(value) -> str:
        return value.strftime("%Y-%m-%d")

    @staticmethod
    def _date(value: str) -> date:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()

    @staticmethod
    def _qty(value):
        if value is None:
            return "--"
        if value == value.to_integral_value():
            return f"{int(value):,}"
        return f"{value:,.4f}".rstrip("0").rstrip(".")

    @classmethod
    def _sq(cls, value):
        if value is None:
            return "--"
        return ("+" if value > 0 else "") + cls._qty(value)

    @staticmethod
    def _money(value):
        return "--" if value is None else f"${value:,.2f}"

    @staticmethod
    def _smoney(value):
        if value is None:
            return "--"
        if value == 0:
            return "$0.00"
        return ("+" if value > 0 else "-") + f"${abs(value):,.2f}"
