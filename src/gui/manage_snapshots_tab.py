"""Desktop screen for managing imported brokerage snapshots."""

from __future__ import annotations

import tkinter as tk
from decimal import Decimal, InvalidOperation
from tkinter import messagebox, ttk

from src.database import get_session
from src.database_init import initialize_database
from src.services.snapshot_management_service import SnapshotManagementService


class ManageSnapshotsTab(ttk.Frame):
    """Review imported snapshots and edit external cash flows."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        self.account_var = tk.StringVar()
        self.added_var = tk.StringVar(value="0.00")
        self.withdrawn_var = tk.StringVar(value="0.00")
        self.status_var = tk.StringVar()
        self._accounts = []
        self._snapshot_ids: dict[str, int] = {}
        self._snapshot_rows: dict[str, tuple[int, Decimal, Decimal]] = {}

        ttk.Label(
            self,
            text="Manage Snapshots",
            font=("Segoe UI", 18, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Label(
            self,
            text=(
                "These are brokerage Excel imports. Daily portfolio updates "
                "do not create entries here. Record only external money "
                "added to or withdrawn from the account since the previous snapshot."
            ),
            wraplength=950,
        ).grid(row=1, column=0, sticky="w", pady=(0, 15))

        controls = ttk.Frame(self)
        controls.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        controls.columnconfigure(1, weight=1)

        ttk.Label(controls, text="Account:").grid(row=0, column=0, padx=(0, 8))
        self.account_combo = ttk.Combobox(
            controls,
            textvariable=self.account_var,
            state="readonly",
            width=55,
        )
        self.account_combo.grid(row=0, column=1, sticky="w")
        self.account_combo.bind("<<ComboboxSelected>>", self._account_changed)
        ttk.Button(controls, text="Refresh", command=self.refresh).grid(
            row=0, column=2, padx=(10, 0)
        )

        body = ttk.Frame(self)
        body.grid(row=3, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        columns = ("date", "value", "added", "withdrawn")
        self.tree = ttk.Treeview(body, columns=columns, show="headings", height=16)
        self.tree.heading("date", text="Snapshot Date")
        self.tree.heading("value", text="Portfolio Value")
        self.tree.heading("added", text="$ Added")
        self.tree.heading("withdrawn", text="$ Withdrawn")
        self.tree.column("date", width=190)
        self.tree.column("value", width=170, anchor="e")
        self.tree.column("added", width=140, anchor="e")
        self.tree.column("withdrawn", width=140, anchor="e")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self._snapshot_selected)

        scrollbar = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        editor = ttk.LabelFrame(self, text="Selected Snapshot — External Cash Flow")
        editor.grid(row=4, column=0, sticky="ew", pady=(12, 0))
        editor.columnconfigure(1, weight=1)

        ttk.Label(editor, text="$ Added:").grid(row=0, column=0, padx=8, pady=8)
        ttk.Entry(editor, textvariable=self.added_var, width=18).grid(row=0, column=1, sticky="w", pady=8)
        ttk.Label(editor, text="$ Withdrawn:").grid(row=0, column=2, padx=(25, 8), pady=8)
        ttk.Entry(editor, textvariable=self.withdrawn_var, width=18).grid(row=0, column=3, sticky="w", pady=8)
        ttk.Button(editor, text="Save Cash Flow", command=self._save).grid(row=0, column=4, padx=12, pady=8)
        ttk.Label(editor, textvariable=self.status_var).grid(row=1, column=0, columnspan=5, sticky="w", padx=8, pady=(0, 8))

        self.after_idle(self.refresh)

    def refresh(self) -> None:
        """Reload accounts and snapshots from the shared service."""
        try:
            initialize_database()
            session = get_session()
            try:
                service = SnapshotManagementService(session)
                self._accounts = service.get_accounts()
                current_key = self.account_var.get()
                labels = [account.label for account in self._accounts]
                self.account_combo["values"] = labels
                if current_key in labels:
                    self.account_var.set(current_key)
                elif labels:
                    self.account_var.set(labels[0])
                else:
                    self.account_var.set("")
                self._load_snapshots(service)
            finally:
                session.close()
        except Exception as exc:
            messagebox.showerror("Manage Snapshots", f"Unable to load snapshots:\n\n{type(exc).__name__}: {exc}")

    def _selected_account_id(self) -> int | None:
        label = self.account_var.get()
        for account in self._accounts:
            if account.label == label:
                return account.account_id
        return None

    def _load_snapshots(self, service: SnapshotManagementService) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._snapshot_ids.clear()
        self._snapshot_rows.clear()
        account_id = self._selected_account_id()
        if account_id is None:
            return
        for snapshot in service.get_snapshots(account_id):
            iid = str(snapshot.id)
            value = "—" if snapshot.total_value is None else f"${snapshot.total_value:,.2f}"
            self.tree.insert(
                "",
                "end",
                iid=iid,
                values=(
                    snapshot.snapshot_date.strftime("%Y-%m-%d"),
                    value,
                    f"${snapshot.external_added:,.2f}",
                    f"${snapshot.external_withdrawn:,.2f}",
                ),
            )
            self._snapshot_ids[iid] = snapshot.id
            self._snapshot_rows[iid] = (snapshot.id, snapshot.external_added, snapshot.external_withdrawn)
        self.status_var.set("Select a snapshot to edit its cash flow.")

    def _account_changed(self, _event=None) -> None:
        self.refresh()

    def _snapshot_selected(self, _event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        row = self._snapshot_rows.get(selection[0])
        if row is None:
            return
        _, added, withdrawn = row
        self.added_var.set(f"{added:.2f}")
        self.withdrawn_var.set(f"{withdrawn:.2f}")
        self.status_var.set("Edit the amounts and click Save Cash Flow.")

    def _save(self) -> None:
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Manage Snapshots", "Select a snapshot first.")
            return
        try:
            added = Decimal(self.added_var.get().strip() or "0")
            withdrawn = Decimal(self.withdrawn_var.get().strip() or "0")
        except (InvalidOperation, ValueError):
            messagebox.showerror("Manage Snapshots", "Enter valid dollar amounts.")
            return
        if added < 0 or withdrawn < 0:
            messagebox.showerror("Manage Snapshots", "Dollar amounts cannot be negative.")
            return

        snapshot_id = self._snapshot_ids[selection[0]]
        try:
            session = get_session()
            try:
                SnapshotManagementService(session).update_cash_flow(
                    snapshot_id,
                    added,
                    withdrawn,
                )
            finally:
                session.close()
            self.status_var.set("Cash flow saved.")
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Manage Snapshots", f"Unable to save:\n\n{type(exc).__name__}: {exc}")
