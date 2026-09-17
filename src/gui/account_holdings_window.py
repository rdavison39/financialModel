"""Shared account detail window for the Financial Model GUI."""

from __future__ import annotations

import tkinter as tk
from decimal import Decimal
from tkinter import ttk


def show_account_holdings(
    parent: tk.Misc,
    account_number: str,
    account_name: str,
    portfolio,
    current_holdings,
    current_cash,
    current_total: Decimal,
    current_daily_change: Decimal,
) -> tk.Toplevel:
    """Show the single consolidated account/holdings window."""

    window = tk.Toplevel(parent)
    window.title(f"Account - {account_number} - {account_name}" if account_name else f"Account - {account_number}")
    window.geometry("1550x760")
    window.minsize(1200, 600)
    window.columnconfigure(0, weight=1)
    window.rowconfigure(3, weight=1)

    def money(value: Decimal | None) -> str:
        if value is None:
            return "--"
        return f"${Decimal(str(value)):,.2f}"

    def signed_money(value: Decimal | None) -> str:
        if value is None:
            return "--"
        value = Decimal(str(value))
        if value >= 0:
            return f"+${value:,.2f}"
        return f"-${abs(value):,.2f}"

    def percent(value: Decimal | None) -> str:
        if value is None:
            return "--"
        return f"{Decimal(str(value)):+.2f}%"

    # -------------------------------------------------------------
    # Header
    # -------------------------------------------------------------
    header = ttk.Frame(window)
    header.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 5))
    header.columnconfigure(1, weight=1)

    ttk.Label(
        header,
        text=f"Account {account_number}" + (f" - {account_name}" if account_name else ""),
        font=("Segoe UI", 16, "bold"),
    ).grid(row=0, column=0, sticky="w")

    ttk.Label(
        header,
        text=f"Snapshot: {portfolio.snapshot_date:%Y-%m-%d}",
        font=("Segoe UI", 10),
    ).grid(row=0, column=1, sticky="e")

    # -------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------
    summary = ttk.LabelFrame(window, text="Account Summary", padding=8)
    summary.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 5))
    for col in (1, 3, 5, 7):
        summary.columnconfigure(col, weight=1)

    total_cost = sum(
        (
            h.market_value - (h.unrealized_gain or Decimal("0"))
            for h in portfolio.holdings
        ),
        Decimal("0"),
    )
    total_gain = current_total - total_cost
    total_gain_pct = total_gain / total_cost * Decimal("100") if total_cost else Decimal("0")
    previous_value = current_total - current_daily_change
    total_daily_pct = (
        current_daily_change / previous_value * Decimal("100")
        if previous_value
        else Decimal("0")
    )

    summary_items = (
        ("Market Value:", money(current_total), "black"),
        ("Cost:", money(total_cost), "black"),
        (
            "Unrealized Gain:",
            f"{signed_money(total_gain)} ({percent(total_gain_pct)})",
            "black",
        ),
        (
            "Today:",
            f"{signed_money(current_daily_change)} ({percent(total_daily_pct)})",
            "green" if current_daily_change > 0 else "red" if current_daily_change < 0 else "black",
        ),
    )

    for index, (label, value, fg) in enumerate(summary_items):
        base = index * 2
        ttk.Label(summary, text=label, font=("Segoe UI", 10, "bold")).grid(
            row=0, column=base, sticky="e", padx=(5, 5)
        )
        tk.Label(
            summary,
            text=value,
            font=("Segoe UI", 11, "bold"),
            fg=fg,
            bg=summary.winfo_toplevel().cget("bg"),
        ).grid(row=0, column=base + 1, sticky="w", padx=(0, 20))

    # -------------------------------------------------------------
    # Cash
    # -------------------------------------------------------------
    cash_frame = ttk.LabelFrame(window, text="Cash", padding=5)
    cash_frame.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 5))

    cash_tree = ttk.Treeview(
        cash_frame,
        columns=("currency", "amount", "cad_value"),
        show="headings",
        height=max(1, len(current_cash)),
    )
    for col, heading in (("currency", "Currency"), ("amount", "Amount"), ("cad_value", "CAD Value")):
        cash_tree.heading(col, text=heading)
    cash_tree.column("currency", width=120, anchor="center", stretch=False)
    cash_tree.column("amount", width=180, anchor="e", stretch=False)
    cash_tree.column("cad_value", width=180, anchor="e", stretch=False)
    cash_tree.grid(row=0, column=0, sticky="w")

    for item in current_cash:
        cash_tree.insert("", "end", values=(item.currency, money(item.amount), money(item.current_cad_value)))

    total_cash = sum((item.current_cad_value for item in current_cash), Decimal("0"))
    ttk.Label(
        cash_frame,
        text=f"Total Cash (CAD): {money(total_cash)}",
        font=("Segoe UI", 10, "bold"),
    ).grid(row=0, column=1, sticky="e", padx=(20, 5))
    cash_frame.columnconfigure(1, weight=1)

    # -------------------------------------------------------------
    # Holdings — a canvas/grid is used so individual cells can have
    # independent colours. Treeview tags colour an entire row and would
    # therefore make the company, quantity, etc. green/red as well.
    # -------------------------------------------------------------
    holdings_frame = ttk.LabelFrame(window, text="Holdings", padding=5)
    holdings_frame.grid(row=3, column=0, sticky="nsew", padx=8, pady=(0, 5))
    holdings_frame.columnconfigure(0, weight=1)
    holdings_frame.rowconfigure(0, weight=1)

    canvas = tk.Canvas(holdings_frame, highlightthickness=0)
    canvas.grid(row=0, column=0, sticky="nsew")
    vbar = ttk.Scrollbar(holdings_frame, orient="vertical", command=canvas.yview)
    vbar.grid(row=0, column=1, sticky="ns")
    hbar = ttk.Scrollbar(holdings_frame, orient="horizontal", command=canvas.xview)
    hbar.grid(row=1, column=0, sticky="ew")
    canvas.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)

    table = tk.Frame(canvas, bg="white")
    canvas_window = canvas.create_window((0, 0), window=table, anchor="nw")

    columns = (
        ("Symbol", 150),
        ("Company", 300),
        ("Quantity", 120),
        ("Average Cost", 140),
        ("Price", 120),
        ("Market Value", 160),
        ("Unrealized Gain", 170),
        ("Gain %", 100),
        ("Today", 120),
        ("Today %", 100),
    )

    for col, (heading, width) in enumerate(columns):
        tk.Label(
            table,
            text=heading,
            width=max(1, width // 9),
            anchor="center",
            relief="groove",
            bd=1,
            bg="#e8e6e0",
            fg="black",
            font=("Segoe UI", 9, "bold"),
        ).grid(row=0, column=col, sticky="nsew")
        table.grid_columnconfigure(col, minsize=width, weight=0)

    current_by_symbol = {item.symbol: item for item in current_holdings}
    any_unavailable = False

    for row_index, holding in enumerate(sorted(portfolio.holdings, key=lambda h: h.symbol), start=1):
        current = current_by_symbol.get(holding.symbol)
        current_price = current.price if current else holding.price
        current_market_value = current.market_value if current else holding.market_value
        cost = holding.market_value - (holding.unrealized_gain or Decimal("0"))
        current_gain = current_market_value - cost
        current_gain_pct = current_gain / cost * Decimal("100") if cost else Decimal("0")
        today = current.daily_change if current and current.daily_change is not None else Decimal("0")
        today_pct = current.daily_change_percent if current and current.daily_change_percent is not None else Decimal("0")
        unavailable = current is not None and not current.is_current
        any_unavailable = any_unavailable or unavailable

        price_fg = "#e87500" if unavailable else "black"
        today_fg = "green" if today > 0 else "red" if today < 0 else "black"
        quantity = f"{holding.quantity:,.6f}".rstrip("0").rstrip(".")

        values = (
            holding.symbol,
            holding.company_name,
            quantity,
            money(holding.average_cost),
            money(current_price) + (" *" if unavailable else ""),
            money(current_market_value),
            signed_money(current_gain),
            percent(current_gain_pct),
            signed_money(today),
            percent(today_pct),
        )
        colors = ("black", "black", "black", "black", price_fg, "black", "black", "black", today_fg, today_fg)

        for col, ((_, width), value, fg) in enumerate(zip(columns, values, colors)):
            anchor = "e" if col >= 2 else "w"
            tk.Label(
                table,
                text=value,
                width=max(1, width // 9),
                anchor=anchor,
                padx=4,
                pady=2,
                bg="white",
                fg=fg,
                font=("Segoe UI", 9),
            ).grid(row=row_index, column=col, sticky="nsew")

    def on_table_configure(_event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))

    table.bind("<Configure>", on_table_configure)

    def on_canvas_configure(event):
        canvas.itemconfigure(canvas_window, height=max(event.height, table.winfo_reqheight()))

    canvas.bind("<Configure>", on_canvas_configure)

    note = tk.Label(
        window,
        text=("* Yahoo price unavailable — imported brokerage price used" if any_unavailable else "Current prices retrieved from Yahoo Finance."),
        fg="#e87500" if any_unavailable else "black",
        anchor="w",
        font=("Segoe UI", 9),
    )
    note.grid(row=4, column=0, sticky="w", padx=8, pady=(0, 3))

    ttk.Button(window, text="Close", command=window.destroy).grid(
        row=5, column=0, sticky="e", padx=8, pady=(0, 8)
    )

    return window
