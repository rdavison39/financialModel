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
    """Compare portfolio positions between two dates."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        # ---------------------------------------------------------
        # Title
        # ---------------------------------------------------------

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

        # ---------------------------------------------------------
        # Date controls
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
        ).pack(
            side="left",
        )

        # ---------------------------------------------------------
        # Summary
        # ---------------------------------------------------------

        summary = ttk.LabelFrame(
            self,
            text="Portfolio Summary",
            padding=10,
        )

        summary.grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(0, 15),
        )

        summary.columnconfigure(1, weight=1)

        ttk.Label(
            summary,
            text="First Date Value:",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 20),
            pady=5,
        )

        self.first_value_label = ttk.Label(
            summary,
            text="$0.00",
            font=("Segoe UI", 11, "bold"),
        )

        self.first_value_label.grid(
            row=0,
            column=1,
            sticky="w",
            pady=5,
        )

        ttk.Label(
            summary,
            text="Second Date Value:",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=(0, 20),
            pady=5,
        )

        self.second_value_label = ttk.Label(
            summary,
            text="$0.00",
            font=("Segoe UI", 11, "bold"),
        )

        self.second_value_label.grid(
            row=1,
            column=1,
            sticky="w",
            pady=5,
        )

        ttk.Label(
            summary,
            text="Value Difference:",
        ).grid(
            row=2,
            column=0,
            sticky="w",
            padx=(0, 20),
            pady=5,
        )

        self.difference_value_label = ttk.Label(
            summary,
            text="$0.00",
            font=("Segoe UI", 11, "bold"),
        )

        self.difference_value_label.grid(
            row=2,
            column=1,
            sticky="w",
            pady=5,
        )

        # ---------------------------------------------------------
        # Position differences
        # ---------------------------------------------------------

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
            width=150,
        )

        self.positions_tree.column(
            "first_quantity",
            width=180,
            anchor="e",
        )

        self.positions_tree.column(
            "second_quantity",
            width=180,
            anchor="e",
        )

        self.positions_tree.column(
            "difference",
            width=180,
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
            yscrollcommand=scrollbar.set
        )

        # ---------------------------------------------------------
        # Status
        # ---------------------------------------------------------

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

    # -------------------------------------------------------------
    # Comparison
    # -------------------------------------------------------------

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
                service = PortfolioComparisonService(
                    session
                )

                result = service.compare(
                    first_date=first_date,
                    second_date=second_date,
                )

            finally:
                session.close()

            self._display_result(result)

        except Exception as exc:
            self.status_label.configure(
                text=(
                    f"Error: {type(exc).__name__}: {exc}"
                )
            )

    # -------------------------------------------------------------
    # Display
    # -------------------------------------------------------------

    def _display_result(self, result) -> None:
        """Display comparison results."""

        first_value = self._get_value(
            result,
            "first_total_value",
            Decimal("0"),
        )

        second_value = self._get_value(
            result,
            "second_total_value",
            Decimal("0"),
        )

        difference = second_value - first_value

        self.first_value_label.configure(
            text=self._format_currency(first_value)
        )

        self.second_value_label.configure(
            text=self._format_currency(second_value)
        )

        self.difference_value_label.configure(
            text=self._format_currency(difference)
        )

        # Clear existing positions.
        for item in self.positions_tree.get_children():
            self.positions_tree.delete(item)

        positions = self._get_value(
            result,
            "position_differences",
            [],
        )

        if isinstance(positions, dict):
            positions = [
                {
                    "symbol": symbol,
                    "first_quantity": quantities[0],
                    "second_quantity": quantities[1],
                    "difference": (
                        quantities[1] - quantities[0]
                    ),
                }
                for symbol, quantities in positions.items()
            ]

        for position in positions:
            if isinstance(position, dict):
                symbol = position.get(
                    "symbol",
                    "",
                )

                first_quantity = position.get(
                    "first_quantity",
                    position.get(
                        "quantity_first",
                        Decimal("0"),
                    ),
                )

                second_quantity = position.get(
                    "second_quantity",
                    position.get(
                        "quantity_second",
                        Decimal("0"),
                    ),
                )

                position_difference = position.get(
                    "difference",
                    Decimal(str(second_quantity))
                    - Decimal(str(first_quantity)),
                )

            else:
                symbol = getattr(
                    position,
                    "symbol",
                    "",
                )

                first_quantity = getattr(
                    position,
                    "first_quantity",
                    getattr(
                        position,
                        "quantity_first",
                        Decimal("0"),
                    ),
                )

                second_quantity = getattr(
                    position,
                    "second_quantity",
                    getattr(
                        position,
                        "quantity_second",
                        Decimal("0"),
                    ),
                )

                position_difference = getattr(
                    position,
                    "difference",
                    Decimal(str(second_quantity))
                    - Decimal(str(first_quantity)),
                )

            self.positions_tree.insert(
                "",
                "end",
                values=(
                    symbol,
                    self._format_quantity(
                        first_quantity
                    ),
                    self._format_quantity(
                        second_quantity
                    ),
                    self._format_quantity(
                        position_difference
                    ),
                ),
            )

        self.status_label.configure(
            text=(
                f"Comparison complete: "
                f"{len(positions)} position(s)."
            )
        )

    # -------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------

    @staticmethod
    def _get_value(
        result,
        attribute: str,
        default,
    ):
        """Read a value from an object or dictionary."""

        if isinstance(result, dict):
            return result.get(
                attribute,
                default,
            )

        return getattr(
            result,
            attribute,
            default,
        )

    @staticmethod
    def _format_currency(value) -> str:
        """Format a value as currency."""

        try:
            amount = Decimal(str(value))
        except Exception:
            amount = Decimal("0")

        return f"${amount:,.2f}"

    @staticmethod
    def _format_quantity(value) -> str:
        """Format a quantity."""

        try:
            quantity = Decimal(str(value))
        except Exception:
            quantity = Decimal("0")

        return f"{quantity:,.6f}".rstrip("0").rstrip(".")