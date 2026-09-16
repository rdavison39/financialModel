"""
Comparison tab for the Financial Model GUI.
"""

import tkinter as tk
from datetime import date, timedelta
from decimal import Decimal
from tkinter import ttk

from src.database import get_session
from src.database_init import initialize_database
from src.services.portfolio_comparison_service import (
    PortfolioComparisonService,
)


class ComparisonTab(ttk.Frame):
    """Compare portfolio values and positions between two dates."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        self._build_ui()

    def _build_ui(self) -> None:
        """Build the comparison page."""

        ttk.Label(
            self,
            text="Portfolio Comparison",
            font=("Segoe UI", 18, "bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 20),
        )

        # ------------------------------------------------------------
        # Date controls
        # ------------------------------------------------------------

        controls = ttk.Frame(self)
        controls.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(0, 15),
        )

        ttk.Label(
            controls,
            text="First Date:",
        ).pack(
            side="left",
            padx=(0, 5),
        )

        self.first_date = tk.StringVar(
            value=(
                date.today() - timedelta(days=30)
            ).isoformat()
        )

        ttk.Entry(
            controls,
            textvariable=self.first_date,
            width=12,
        ).pack(
            side="left",
            padx=(0, 20),
        )

        ttk.Label(
            controls,
            text="Second Date:",
        ).pack(
            side="left",
            padx=(0, 5),
        )

        self.second_date = tk.StringVar(
            value=date.today().isoformat()
        )

        ttk.Entry(
            controls,
            textvariable=self.second_date,
            width=12,
        ).pack(
            side="left",
            padx=(0, 20),
        )

        ttk.Button(
            controls,
            text="Compare",
            command=self._compare,
        ).pack(side="left")

        # ------------------------------------------------------------
        # Portfolio summary
        # ------------------------------------------------------------

        summary_frame = ttk.LabelFrame(
            self,
            text="Portfolio Summary",
            padding=10,
        )

        summary_frame.grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(0, 15),
        )

        ttk.Label(
            summary_frame,
            text="First Date Value:",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 30),
            pady=5,
        )

        self.first_value_label = ttk.Label(
            summary_frame,
            text="Not available",
            font=("Segoe UI", 10, "bold"),
        )

        self.first_value_label.grid(
            row=0,
            column=1,
            sticky="w",
            pady=5,
        )

        ttk.Label(
            summary_frame,
            text="Second Date Value:",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=(0, 30),
            pady=5,
        )

        self.second_value_label = ttk.Label(
            summary_frame,
            text="Not available",
            font=("Segoe UI", 10, "bold"),
        )

        self.second_value_label.grid(
            row=1,
            column=1,
            sticky="w",
            pady=5,
        )

        ttk.Label(
            summary_frame,
            text="Value Difference:",
        ).grid(
            row=2,
            column=0,
            sticky="w",
            padx=(0, 30),
            pady=5,
        )

        self.value_difference_label = ttk.Label(
            summary_frame,
            text="Not available",
            font=("Segoe UI", 10, "bold"),
        )

        self.value_difference_label.grid(
            row=2,
            column=1,
            sticky="w",
            pady=5,
        )

        # ------------------------------------------------------------
        # Position table
        # ------------------------------------------------------------

        positions_frame = ttk.LabelFrame(
            self,
            text="Position Quantity Differences",
            padding=10,
        )

        positions_frame.grid(
            row=3,
            column=0,
            sticky="nsew",
        )

        positions_frame.columnconfigure(0, weight=1)
        positions_frame.rowconfigure(0, weight=1)

        self.positions_tree = ttk.Treeview(
            positions_frame,
            columns=(
                "symbol",
                "company",
                "first_quantity",
                "second_quantity",
                "difference",
            ),
            show="headings",
        )

        self.positions_tree.heading(
            "symbol",
            text="Symbol",
        )

        self.positions_tree.heading(
            "company",
            text="Company",
        )

        self.positions_tree.heading(
            "first_quantity",
            text="First Date Quantity",
        )

        self.positions_tree.heading(
            "second_quantity",
            text="Second Date Quantity",
        )

        self.positions_tree.heading(
            "difference",
            text="Quantity Difference",
        )

        self.positions_tree.column(
            "symbol",
            width=130,
        )

        self.positions_tree.column(
            "company",
            width=250,
        )

        self.positions_tree.column(
            "first_quantity",
            width=160,
            anchor="e",
        )

        self.positions_tree.column(
            "second_quantity",
            width=160,
            anchor="e",
        )

        self.positions_tree.column(
            "difference",
            width=160,
            anchor="e",
        )

        self.positions_tree.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        scrollbar = ttk.Scrollbar(
            positions_frame,
            orient="vertical",
            command=self.positions_tree.yview,
        )

        scrollbar.grid(
            row=0,
            column=1,
            sticky="ns",
        )

        self.positions_tree.configure(
            yscrollcommand=scrollbar.set,
        )

        # ------------------------------------------------------------
        # Status
        # ------------------------------------------------------------

        self.status_label = ttk.Label(
            self,
            text="",
        )

        self.status_label.grid(
            row=4,
            column=0,
            sticky="w",
            pady=(10, 0),
        )

    def _compare(self) -> None:
        """Compare portfolio values and positions."""

        try:
            first_date = date.fromisoformat(
                self.first_date.get().strip()
            )

            second_date = date.fromisoformat(
                self.second_date.get().strip()
            )

        except ValueError:
            self.status_label.configure(
                text="Dates must be in YYYY-MM-DD format."
            )
            return

        if first_date > second_date:
            self.status_label.configure(
                text="First date cannot be after second date."
            )
            return

        try:
            initialize_database()

            session = get_session()

            try:
                service = PortfolioComparisonService(session)

                result = service.compare(
                    first_date=first_date,
                    second_date=second_date,
                    account_id=None,
                )

            finally:
                session.close()

            self._display_summary(result)
            self._display_positions(result.positions)

            self.status_label.configure(
                text=(
                    f"Comparison complete: "
                    f"{len(result.positions)} position(s)."
                )
            )

        except Exception as exc:
            self.status_label.configure(
                text=f"Error: {type(exc).__name__}: {exc}"
            )

    def _display_summary(self, result) -> None:
        """Display portfolio values and difference."""

        self.first_value_label.configure(
            text=self._format_money(result.first_value)
        )

        self.second_value_label.configure(
            text=self._format_money(result.second_value)
        )

        self.value_difference_label.configure(
            text=self._format_money(result.value_difference)
        )

    def _display_positions(self, positions) -> None:
        """Display position quantity differences."""

        for item in self.positions_tree.get_children():
            self.positions_tree.delete(item)

        for position in positions:
            self.positions_tree.insert(
                "",
                "end",
                values=(
                    position.symbol,
                    position.company_name,
                    self._format_quantity(
                        position.first_quantity
                    ),
                    self._format_quantity(
                        position.second_quantity
                    ),
                    self._format_quantity(
                        position.quantity_difference
                    ),
                ),
            )

    @staticmethod
    def _format_money(
        value: Decimal | None,
    ) -> str:
        """Format a portfolio value."""

        if value is None:
            return "Not available"

        return f"${value:,.2f}"

    @staticmethod
    def _format_quantity(
        value: Decimal,
    ) -> str:
        """Format a quantity."""

        return (
            f"{Decimal(str(value)):,.6f}"
            .rstrip("0")
            .rstrip(".")
        )