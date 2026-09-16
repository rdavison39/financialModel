"""
Graphs tab for the Financial Model GUI.
"""

import tkinter as tk
from datetime import date, timedelta
from decimal import Decimal
from tkinter import ttk

from src.database import get_session
from sqlalchemy import select

from src.database_init import initialize_database
from src.models.account import Account
from src.models.brokerage import Brokerage
from src.services.portfolio_history_service import PortfolioHistoryService


class GraphsTab(ttk.Frame):
    """Display portfolio value history."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        self._account_ids: dict[str, int | None] = {}

        self._build_ui()

        # Load accounts and the default date range when the tab is created.
        self.after(100, self._initialize)

    # -------------------------------------------------------------
    # UI
    # -------------------------------------------------------------

    def _build_ui(self) -> None:
        """Build the graphs page."""

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
            text="Account:",
        ).pack(
            side="left",
            padx=(0, 5),
        )

        self.account_var = tk.StringVar()

        self.account_combo = ttk.Combobox(
            controls,
            textvariable=self.account_var,
            state="readonly",
            width=42,
        )
        self.account_combo.pack(
            side="left",
            padx=(0, 20),
        )
        self.account_combo.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._refresh(),
        )

        ttk.Label(
            controls,
            text="Start Date:",
        ).pack(
            side="left",
            padx=(0, 5),
        )

        self.start_date = tk.StringVar(
            value=(
                date.today() - timedelta(days=30)
            ).isoformat()
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
        # Graph
        # ---------------------------------------------------------

        graph_frame = ttk.LabelFrame(
            self,
            text="Portfolio Value",
            padding=10,
        )

        graph_frame.grid(
            row=2,
            column=0,
            sticky="nsew",
            pady=(0, 15),
        )

        graph_frame.columnconfigure(0, weight=1)
        graph_frame.rowconfigure(0, weight=1)

        self.graph_canvas = tk.Canvas(
            graph_frame,
            height=350,
            background="white",
            highlightthickness=1,
        )

        self.graph_canvas.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        # ---------------------------------------------------------
        # History table
        # ---------------------------------------------------------

        history_frame = ttk.LabelFrame(
            self,
            text="Portfolio Value History",
            padding=10,
        )

        history_frame.grid(
            row=3,
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
            height=8,
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

        # Redraw the graph when the window is resized.
        self.graph_canvas.bind(
            "<Configure>",
            self._on_graph_resize,
        )

        self._last_history = []

    # -------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------

    def _initialize(self) -> None:
        """Load the account selector and then refresh the graph."""
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

            self._account_ids = {
                "Consolidated Portfolio": None,
            }

            account_names = [
                "Consolidated Portfolio",
            ]

            for account, brokerage in rows:
                display_name = (
                    f"{brokerage.name} - "
                    f"{account.account_number} - "
                    f"{account.name}"
                )

                # Account numbers are unique within a brokerage, so this
                # provides a stable display value for the selector.
                self._account_ids[display_name] = account.id
                account_names.append(display_name)

            self.account_combo["values"] = account_names
            self.account_var.set("Consolidated Portfolio")

            self._refresh()

        except Exception as exc:
            self.status_label.configure(
                text=f"Error loading accounts: {type(exc).__name__}: {exc}"
            )

    # -------------------------------------------------------------
    # Refresh
    # -------------------------------------------------------------

    def _refresh(self) -> None:
        """Refresh the portfolio history and graph."""

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

                account_id = self._account_ids.get(
                    self.account_var.get(),
                    None,
                )

                history = service.get_history(
                    start_date=start_date,
                    end_date=end_date,
                    account_id=account_id,
                )

            finally:
                session.close()

            self._last_history = history

            self._display_history(history)
            self._draw_graph(history)

            selected_account = self.account_var.get() or "Consolidated Portfolio"

            self.status_label.configure(
                text=f"{len(history)} valuation(s) found for {selected_account}."
            )

        except Exception as exc:
            self.status_label.configure(
                text=f"Error: {type(exc).__name__}: {exc}"
            )

    # -------------------------------------------------------------
    # Display
    # -------------------------------------------------------------

    def _display_history(self, history) -> None:
        """Display portfolio history in the table."""

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

    # -------------------------------------------------------------
    # Graph
    # -------------------------------------------------------------

    def _draw_graph(self, history) -> None:
        """Draw the portfolio value graph."""

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

        # ---------------------------------------------------------
        # Graph dimensions
        # ---------------------------------------------------------

        left = 80
        right = 30
        top = 30
        bottom = 55

        graph_width = width - left - right
        graph_height = height - top - bottom

        if graph_width <= 0 or graph_height <= 0:
            return

        values = [
            Decimal(str(snapshot.total_value))
            for snapshot in history
        ]

        minimum = min(values)
        maximum = max(values)

        # Give the graph some vertical breathing room.
        if minimum == maximum:
            padding = (
                Decimal("1000")
                if minimum == 0
                else abs(minimum) * Decimal("0.05")
            )
        else:
            padding = (maximum - minimum) * Decimal("0.10")

        graph_min = max(
            Decimal("0"),
            minimum - padding,
        )

        graph_max = maximum + padding

        if graph_max == graph_min:
            graph_max = graph_min + Decimal("1")

        # ---------------------------------------------------------
        # Axes
        # ---------------------------------------------------------

        canvas.create_line(
            left,
            top,
            left,
            height - bottom,
        )

        canvas.create_line(
            left,
            height - bottom,
            width - right,
            height - bottom,
        )

        # ---------------------------------------------------------
        # Horizontal grid lines and Y labels
        # ---------------------------------------------------------

        grid_lines = 5

        for i in range(grid_lines + 1):
            fraction = i / grid_lines

            y = (
                top
                + fraction * graph_height
            )

            value = (
                graph_max
                - (graph_max - graph_min)
                * Decimal(str(fraction))
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

        # ---------------------------------------------------------
        # X positions
        # ---------------------------------------------------------

        count = len(history)

        points = []

        for index, snapshot in enumerate(history):
            if count == 1:
                x = left + graph_width / 2
            else:
                x = (
                    left
                    + (index / (count - 1))
                    * graph_width
                )

            value = Decimal(
                str(snapshot.total_value)
            )

            value_fraction = float(
                (value - graph_min)
                / (graph_max - graph_min)
            )

            y = (
                top
                + (1 - value_fraction)
                * graph_height
            )

            points.append(
                (x, y)
            )

        # ---------------------------------------------------------
        # X-axis labels
        # ---------------------------------------------------------

        label_count = min(6, count)

        if label_count == 1:
            label_indexes = [0]
        else:
            label_indexes = [
                round(
                    i * (count - 1)
                    / (label_count - 1)
                )
                for i in range(label_count)
            ]

        for index in label_indexes:
            snapshot = history[index]

            if count == 1:
                x = left + graph_width / 2
            else:
                x = (
                    left
                    + (index / (count - 1))
                    * graph_width
                )

            canvas.create_text(
                x,
                height - bottom + 20,
                text=snapshot.snapshot_date.strftime(
                    "%Y-%m-%d"
                ),
                anchor="n",
            )

        # ---------------------------------------------------------
        # Portfolio line
        # ---------------------------------------------------------

        if len(points) >= 2:
            flattened = []

            for x, y in points:
                flattened.extend([x, y])

            canvas.create_line(
                *flattened,
                width=2,
                smooth=False,
            )

        # ---------------------------------------------------------
        # Data points
        # ---------------------------------------------------------

        for index, (x, y) in enumerate(points):
            radius = 3

            canvas.create_oval(
                x - radius,
                y - radius,
                x + radius,
                y + radius,
                fill="black",
            )

            # Only label the final value.
            if index == len(points) - 1:
                canvas.create_text(
                    x,
                    y - 12,
                    text=self._format_axis_value(
                        values[index]
                    ),
                    anchor="s",
                )

    # -------------------------------------------------------------
    # Resize
    # -------------------------------------------------------------

    def _on_graph_resize(self, event) -> None:
        """Redraw the graph when the canvas changes size."""

        if self._last_history:
            self._draw_graph(
                self._last_history
            )

    # -------------------------------------------------------------
    # Formatting
    # -------------------------------------------------------------

    @staticmethod
    def _format_axis_value(value: Decimal) -> str:
        """Format a graph axis value."""

        if abs(value) >= Decimal("1000000"):
            return f"${value / Decimal('1000000'):,.1f}M"

        if abs(value) >= Decimal("1000"):
            return f"${value / Decimal('1000'):,.0f}K"

        return f"${value:,.0f}"