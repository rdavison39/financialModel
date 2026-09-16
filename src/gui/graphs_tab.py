"""
Graphs tab for the Financial Model GUI.
"""

import tkinter as tk
from datetime import date, timedelta
from tkinter import ttk

from src.database import get_session
from src.database_init import initialize_database
from src.services.portfolio_history_service import PortfolioHistoryService


class GraphsTab(ttk.Frame):
    """Display portfolio value history."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # ---------------------------------------------------------
        # Title
        # ---------------------------------------------------------

        ttk.Label(
            self,
            text="Graphs",
            font=("Segoe UI", 18, "bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 20),
        )

        # ---------------------------------------------------------
        # Controls
        # ---------------------------------------------------------

        controls = ttk.Frame(self)
        controls.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(0, 15),
        )

        ttk.Label(
            controls,
            text="Start Date:",
        ).pack(
            side="left",
            padx=(0, 5),
        )

        self.start_date = tk.StringVar(
            value=(date.today() - timedelta(days=30)).isoformat()
        )

        ttk.Entry(
            controls,
            textvariable=self.start_date,
            width=12,
        ).pack(
            side="left",
            padx=(0, 15),
        )

        ttk.Label(
            controls,
            text="End Date:",
        ).pack(
            side="left",
            padx=(0, 5),
        )

        self.end_date = tk.StringVar(
            value=date.today().isoformat()
        )

        ttk.Entry(
            controls,
            textvariable=self.end_date,
            width=12,
        ).pack(
            side="left",
            padx=(0, 15),
        )

        ttk.Button(
            controls,
            text="Refresh",
            command=self._refresh,
        ).pack(
            side="left",
        )

        # ---------------------------------------------------------
        # History
        # ---------------------------------------------------------

        history_frame = ttk.LabelFrame(
            self,
            text="Portfolio Value History",
            padding=10,
        )

        history_frame.grid(
            row=2,
            column=0,
            sticky="nsew",
        )

        history_frame.columnconfigure(0, weight=1)
        history_frame.rowconfigure(0, weight=1)

        self.history_tree = ttk.Treeview(
            history_frame,
            columns=(
                "date",
                "value",
            ),
            show="headings",
        )

        self.history_tree.heading(
            "date",
            text="Date",
        )

        self.history_tree.heading(
            "value",
            text="Portfolio Value",
        )

        self.history_tree.column(
            "date",
            width=150,
        )

        self.history_tree.column(
            "value",
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

        scrollbar.grid(
            row=0,
            column=1,
            sticky="ns",
        )

        self.history_tree.configure(
            yscrollcommand=scrollbar.set
        )

        self.status_label = ttk.Label(
            self,
            text="",
        )

        self.status_label.grid(
            row=3,
            column=0,
            sticky="w",
            pady=(10, 0),
        )

    # -------------------------------------------------------------
    # Refresh
    # -------------------------------------------------------------

    def _refresh(self) -> None:
        """Refresh the portfolio history."""

        try:
            start_date = date.fromisoformat(
                self.start_date.get().strip()
            )

            end_date = date.fromisoformat(
                self.end_date.get().strip()
            )

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

        try:
            initialize_database()

            session = get_session()

            try:
                service = PortfolioHistoryService(
                    session
                )

                history = service.get_history(
                    start_date=start_date,
                    end_date=end_date,
                    account_id=None,
                )

            finally:
                session.close()

            self._display_history(history)

            self.status_label.configure(
                text=f"{len(history)} valuation(s) found."

            )

        except Exception as exc:
            self.status_label.configure(
                text=f"Error: {type(exc).__name__}: {exc}"
            )

    # -------------------------------------------------------------
    # Display
    # -------------------------------------------------------------

    def _display_history(self, history) -> None:
        """Display portfolio history."""

        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        for snapshot in history:
            self.history_tree.insert(
                "",
                "end",
                values=(
                    snapshot.snapshot_date.isoformat(),
                    f"${snapshot.total_value:,.2f}",
                ),
            )