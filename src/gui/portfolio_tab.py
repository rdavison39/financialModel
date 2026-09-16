"""
Portfolio tab for the Financial Model GUI.
"""

import tkinter as tk
from decimal import Decimal
from tkinter import ttk

from src.database import get_session
from src.database_init import initialize_database
from src.services.portfolio_valuation_service import (
    PortfolioValuationService,
)


class PortfolioTab(ttk.Frame):
    """Display current portfolio values."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # ---------------------------------------------------------
        # Title
        # ---------------------------------------------------------

        ttk.Label(
            self,
            text="Portfolio",
            font=("Segoe UI", 18, "bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 20),
        )

        # ---------------------------------------------------------
        # Update button
        # ---------------------------------------------------------

        controls = ttk.Frame(self)
        controls.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(0, 15),
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
        # Portfolio values
        # ---------------------------------------------------------

        values_frame = ttk.LabelFrame(
            self,
            text="Current Portfolio Value",
            padding=15,
        )

        values_frame.grid(
            row=2,
            column=0,
            sticky="nsew",
        )

        values_frame.columnconfigure(0, weight=1)
        values_frame.columnconfigure(1, weight=1)

        self.total_value_label = self._create_value_row(
            values_frame,
            0,
            "Total Portfolio",
        )

        self.bmo_value_label = self._create_value_row(
            values_frame,
            1,
            "BMO",
        )

        self.nesbitt_value_label = self._create_value_row(
            values_frame,
            2,
            "Nesbitt Burns",
        )

        # ---------------------------------------------------------
        # Accounts
        # ---------------------------------------------------------

        accounts_frame = ttk.LabelFrame(
            self,
            text="Accounts",
            padding=10,
        )

        accounts_frame.grid(
            row=3,
            column=0,
            sticky="ew",
            pady=(15, 0),
        )

        accounts_frame.columnconfigure(0, weight=1)

        self.accounts_tree = ttk.Treeview(
            accounts_frame,
            columns=(
                "brokerage",
                "account",
                "name",
                "value",
            ),
            show="headings",
            height=8,
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
            text="Value",
        )

        self.accounts_tree.column(
            "brokerage",
            width=150,
        )

        self.accounts_tree.column(
            "account",
            width=120,
        )

        self.accounts_tree.column(
            "name",
            width=200,
        )

        self.accounts_tree.column(
            "value",
            width=150,
            anchor="e",
        )

        self.accounts_tree.grid(
            row=0,
            column=0,
            sticky="ew",
        )

    # -------------------------------------------------------------
    # UI helpers
    # -------------------------------------------------------------

    def _create_value_row(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
    ) -> ttk.Label:
        """Create a portfolio value display row."""

        ttk.Label(
            parent,
            text=label,
            font=("Segoe UI", 11),
        ).grid(
            row=row,
            column=0,
            sticky="w",
            pady=8,
        )

        value_label = ttk.Label(
            parent,
            text="$0.00",
            font=("Segoe UI", 12, "bold"),
        )

        value_label.grid(
            row=row,
            column=1,
            sticky="e",
            pady=8,
        )

        return value_label

    # -------------------------------------------------------------
    # Portfolio update
    # -------------------------------------------------------------

    def _update_portfolio(self) -> None:
        """Update current portfolio valuations."""

        self.status_label.configure(
            text="Updating..."
        )

        self.update_idletasks()

        try:
            initialize_database()

            session = get_session()

            try:
                service = PortfolioValuationService(session)

                result = service.update_portfolio()

            finally:
                session.close()

            self._display_portfolio(result)

            self.status_label.configure(
                text="Portfolio updated."
            )

        except Exception as exc:
            self.status_label.configure(
                text="Update failed."
            )

            self._show_error(
                f"{type(exc).__name__}: {exc}"
            )

    # -------------------------------------------------------------
    # Display
    # -------------------------------------------------------------

    def _display_portfolio(self, result) -> None:
        """Display valuation results."""

        total_value = self._get_result_value(
            result,
            "total_value",
            Decimal("0"),
        )

        self.total_value_label.configure(
            text=self._format_currency(total_value)
        )

        brokerage_values = self._get_result_value(
            result,
            "brokerage_values",
            {},
        )

        bmo_value = self._find_brokerage_value(
            brokerage_values,
            "BMO",
        )

        nesbitt_value = self._find_brokerage_value(
            brokerage_values,
            "Nesbitt Burns",
        )

        self.bmo_value_label.configure(
            text=self._format_currency(bmo_value)
        )

        self.nesbitt_value_label.configure(
            text=self._format_currency(nesbitt_value)
        )

        self._display_accounts(result)

    def _display_accounts(self, result) -> None:
        """Display account-level portfolio values."""

        for item in self.accounts_tree.get_children():
            self.accounts_tree.delete(item)

        accounts = self._get_result_value(
            result,
            "account_values",
            [],
        )

        if isinstance(accounts, dict):
            accounts = [
                {
                    "brokerage": key,
                    "value": value,
                }
                for key, value in accounts.items()
            ]

        for account in accounts:
            if isinstance(account, dict):
                brokerage = account.get(
                    "brokerage",
                    "",
                )

                account_number = account.get(
                    "account_number",
                    "",
                )

                name = account.get(
                    "name",
                    account_number,
                )

                value = account.get(
                    "value",
                    Decimal("0"),
                )

            else:
                brokerage = getattr(
                    account,
                    "brokerage",
                    "",
                )

                account_number = getattr(
                    account,
                    "account_number",
                    "",
                )

                name = getattr(
                    account,
                    "name",
                    account_number,
                )

                value = getattr(
                    account,
                    "value",
                    Decimal("0"),
                )

            self.accounts_tree.insert(
                "",
                "end",
                values=(
                    brokerage,
                    account_number,
                    name,
                    self._format_currency(value),
                ),
            )

    # -------------------------------------------------------------
    # Result helpers
    # -------------------------------------------------------------

    @staticmethod
    def _get_result_value(
        result,
        attribute: str,
        default,
    ):
        """Read a value from either an object or dictionary."""

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
    def _find_brokerage_value(
        brokerage_values,
        brokerage_name: str,
    ) -> Decimal:
        """Find a brokerage value regardless of result structure."""

        if not brokerage_values:
            return Decimal("0")

        if isinstance(brokerage_values, dict):
            value = brokerage_values.get(
                brokerage_name,
                Decimal("0"),
            )

            return Decimal(str(value))

        for item in brokerage_values:
            if isinstance(item, dict):
                name = item.get(
                    "brokerage",
                    item.get("name", ""),
                )

                if name == brokerage_name:
                    return Decimal(
                        str(
                            item.get(
                                "value",
                                Decimal("0"),
                            )
                        )
                    )

            else:
                name = getattr(
                    item,
                    "brokerage",
                    getattr(item, "name", ""),
                )

                if name == brokerage_name:
                    return Decimal(
                        str(
                            getattr(
                                item,
                                "value",
                                Decimal("0"),
                            )
                        )
                    )

        return Decimal("0")

    @staticmethod
    def _format_currency(value) -> str:
        """Format a value as Canadian currency."""

        try:
            amount = Decimal(str(value))
        except Exception:
            amount = Decimal("0")

        return f"${amount:,.2f}"

    # -------------------------------------------------------------
    # Error handling
    # -------------------------------------------------------------

    def _show_error(self, message: str) -> None:
        """Display an error message."""

        from tkinter import messagebox

        messagebox.showerror(
            "Portfolio Update Error",
            message,
        )