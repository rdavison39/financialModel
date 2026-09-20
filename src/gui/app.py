"""
Main application window for the Financial Model GUI.
"""

import tkinter as tk
from tkinter import ttk

from src.gui.account_comparison_tab import AccountComparisonTab
from src.gui.accounts_tab import AccountsTab
from src.gui.comparison_tab import ComparisonTab
from src.gui.graphs_tab import GraphsTab
from src.gui.import_tab import ImportTab
from src.gui.portfolio_tab import PortfolioTab


class FinancialModelApp(tk.Tk):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()

        self.title("Financial Model")
        self.geometry("1550x900")
        self.minsize(1200, 700)

        self._configure_style()
        self._build_layout()

    def _configure_style(self) -> None:
        """Configure the basic application styling."""
        style = ttk.Style(self)

        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "Title.TLabel",
            font=("Segoe UI", 18, "bold"),
        )

        style.configure(
            "Navigation.TButton",
            font=("Segoe UI", 11),
            padding=(15, 10),
        )

    def _build_layout(self) -> None:
        """Build the main window layout."""
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        navigation = ttk.Frame(self, padding=10)
        navigation.grid(
            row=0,
            column=0,
            sticky="ns",
        )

        # Shared by pages that place account selectors below the navigation
        # buttons.  Keep this reference independent of button labels.
        self.navigation = navigation

        ttk.Label(
            navigation,
            text="Financial Model",
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=(5, 20))

        for text, command in (
            ("Portfolio", self.show_portfolio),
            ("Portfolio History", self.show_graphs),
            ("Account Management", self.show_accounts),
            ("Account History", self.show_account_comparison),
            ("Holdings History", self.show_comparison),
            ("Import", self.show_import),
        ):
            ttk.Button(
                navigation,
                text=text,
                style="Navigation.TButton",
                command=command,
            ).pack(
                fill="x",
                pady=3,
            )

        self.content = ttk.Frame(
            self,
            padding=20,
        )
        self.content.grid(
            row=0,
            column=1,
            sticky="nsew",
        )
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(0, weight=1)

        self.import_page = ImportTab(self.content)
        self.portfolio_page = PortfolioTab(self.content)
        self.accounts_page = AccountsTab(self.content)
        self.graphs_page = GraphsTab(self.content)
        self.account_comparison_page = AccountComparisonTab(
            self.content
        )
        self.comparison_page = ComparisonTab(self.content)

        self.show_portfolio()

    def _hide_pages(self) -> None:
        """Hide all pages."""
        self.import_page.grid_remove()
        self.portfolio_page.grid_remove()
        self.accounts_page.grid_remove()
        self.graphs_page.grid_remove()
        self.account_comparison_page.grid_remove()
        self.comparison_page.grid_remove()

    def _show_page(self, page: ttk.Frame) -> None:
        """Show one page."""
        self._hide_pages()
        page.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

    def show_import(self) -> None:
        """Show the Import page."""
        self._show_page(self.import_page)

    def show_portfolio(self) -> None:
        """Show the Portfolio page."""
        self._show_page(self.portfolio_page)

    def show_accounts(self) -> None:
        """Show the Account Management page."""
        self._show_page(self.accounts_page)

    def show_graphs(self) -> None:
        """Show the Portfolio History page."""
        self._show_page(self.graphs_page)

    def show_account_comparison(self) -> None:
        """Show the Account History page."""
        self._show_page(self.account_comparison_page)

    def show_comparison(self) -> None:
        """Show the Holdings History page."""
        self._show_page(self.comparison_page)


def main() -> None:
    """Start the application."""
    app = FinancialModelApp()
    app.mainloop()


if __name__ == "__main__":
    main()
