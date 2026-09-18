"""Reusable sorting support for Tkinter ttk Treeview widgets."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal, InvalidOperation
from typing import Any

from tkinter import ttk


SortKey = Callable[[str], Any]


def parse_number(value: object) -> Decimal | None:
    """Convert a displayed numeric value to Decimal for sorting."""
    if value is None:
        return None

    text = str(value).strip()
    if not text or text in {"--", "-", "N/A"}:
        return None

    text = text.replace("$", "").replace(",", "").replace("%", "")
    text = text.replace("(", "-").replace(")", "")

    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def parse_text(value: object) -> str:
    """Return a normalized text value for case-insensitive sorting."""
    if value is None:
        return ""
    return str(value).strip().casefold()


def sort_treeview(
    tree: ttk.Treeview,
    column: str,
    *,
    key: SortKey | None = None,
    descending: bool = False,
) -> None:
    """Sort a Treeview by one column while preserving row identifiers.

    ``key`` receives the raw displayed cell value and should return the value
    that should determine the ordering.  Missing values are placed at the end
    regardless of ascending/descending direction.
    """
    children = list(tree.get_children(""))

    if key is None:
        key = parse_text

    keyed = []
    missing = []
    for item_id in children:
        value = tree.set(item_id, column)
        parsed = key(value)
        if parsed is None:
            missing.append(item_id)
        else:
            keyed.append((parsed, item_id))

    keyed.sort(key=lambda item: item[0], reverse=descending)
    ordered = [item_id for _, item_id in keyed] + missing

    for index, item_id in enumerate(ordered):
        tree.move(item_id, "", index)


def bind_sortable_headings(
    tree: ttk.Treeview,
    columns: tuple[str, ...],
    *,
    heading_text: dict[str, str],
    key_for_column: dict[str, SortKey] | None = None,
    on_sorted: Callable[[str, bool], None] | None = None,
) -> None:
    """Make Treeview headings clickable with ascending/descending sorting."""
    key_for_column = key_for_column or {}
    state: dict[str, bool] = {}

    def sort_column(column: str) -> None:
        descending = state.get(column, False)

        sort_treeview(
            tree,
            column,
            key=key_for_column.get(column),
            descending=descending,
        )

        for name in columns:
            arrow = ""
            if name == column:
                arrow = " ▼" if descending else " ▲"
            tree.heading(
                name,
                text=heading_text[name] + arrow,
            )

        if on_sorted is not None:
            on_sorted(column, descending)

        state[column] = not descending

    for column in columns:
        tree.heading(
            column,
            text=heading_text[column],
            command=lambda name=column: sort_column(name),
        )


def numeric_sort_key(value: object) -> Decimal | None:
    """Sort key for currency, percentages, quantities, and other numbers."""
    return parse_number(value)
