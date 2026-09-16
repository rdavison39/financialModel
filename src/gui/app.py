"""
Main application window for the Financial Model GUI.
"""

import tkinter as tk
from tkinter import ttk

from src.gui.graphs_tab import GraphsTab
from src.gui.import_tab import ImportTab
from src.gui.portfolio_tab import PortfolioTab


class FinancialModelApp(tk.Tk):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()

        self.title("Financial Model")
        self.geometry("1100x700")
        self.minsize(900, 600)

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

        # ---------------------------------------------------------
        # Navigation
        # ---------------------------------------------------------

        navigation = ttk.Frame(self, padding=10)
        navigation.grid(
            row=0,
            column=0,
            sticky="ns",
        )

        ttk.Label(
            navigation,
            text="Financial Model",
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=(5, 20))

        ttk.Button(
            navigation,
            text="Import",
            style="Navigation.TButton",
            command=self.show_import,
        ).pack(
            fill="x",
            pady=3,
        )

        ttk.Button(
            navigation,
            text="Portfolio",
            style="Navigation.TButton",
            command=self.show_portfolio,
        ).pack(
            fill="x",
            pady=3,
        )

        ttk.Button(
            navigation,
            text="Graphs",
            style="Navigation.TButton",
            command=self.show_graphs,
        ).pack(
            fill="x",
            pady=3,
        )

        ttk.Button(
            navigation,
            text="Comparison",
            style="Navigation.TButton",
            command=self.show_comparison,
        ).pack(
            fill="x",
            pady=3,
        )

        # ---------------------------------------------------------
        # Content area
        # ---------------------------------------------------------

        self.content = ttk.Frame(
            self,
            padding=20,
        )

        self.content.grid(
            row=0,
            column=1,
            sticky="nsew",
        )

        self.content.columnconfigure(
            0,
            weight=1,
        )

        self.content.rowconfigure(
            0,
            weight=1,
        )

        # ---------------------------------------------------------
        # Pages
        # ---------------------------------------------------------

        self.import_page = ImportTab(
            self.content
        )

        self.portfolio_page = PortfolioTab(
            self.content
        )

        self.graphs_page = GraphsTab(
            self.content
        )

        self.comparison_page = self._create_placeholder(
            "Comparison",
            "Portfolio comparisons will be displayed here.",
        )

        # Start on Import.
        self.show_import()

    # -------------------------------------------------------------
    # Page management
    # -------------------------------------------------------------

    def _hide_pages(self) -> None:
        """Hide all pages."""

        self.import_page.grid_remove()
        self.portfolio_page.grid_remove()
        self.graphs_page.grid_remove()
        self.comparison_page.grid_remove()

    def _show_page(
        self,
        page: ttk.Frame,
    ) -> None:
        """Show one page."""

        self._hide_pages()

        page.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

    # -------------------------------------------------------------
    # Navigation
    # -------------------------------------------------------------

    def show_import(self) -> None:
        """Show the Import page."""
        self._show_page(self.import_page)

    def show_portfolio(self) -> None:
        """Show the Portfolio page."""
        self._show_page(self.portfolio_page)

    def show_graphs(self) -> None:
        """Show the Graphs page."""
        self._show_page(self.graphs_page)

    def show_comparison(self) -> None:
        """Show the Comparison page."""
        self._show_page(self.comparison_page)

    # -------------------------------------------------------------
    # Temporary placeholder pages
    # -------------------------------------------------------------

    def _create_placeholder(
        self,
        title: str,
        message: str,
    ) -> ttk.Frame:
        """Create a temporary page."""

        frame = ttk.Frame(
            self.content
        )

        frame.columnconfigure(
            0,
            weight=1,
        )

        frame.rowconfigure(
            1,
            weight=1,
        )

        ttk.Label(
            frame,
            text=title,
            style="Title.TLabel",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 20),
        )

        ttk.Label(
            frame,
            text=message,
            font=("Segoe UI", 11),
        ).grid(
            row=1,
            column=0,
            sticky="nw",
        )

        return frame


def main() -> None:
    """Start the application."""

    app = FinancialModelApp()
    app.mainloop()


if __name__ == "__main__":
    main()