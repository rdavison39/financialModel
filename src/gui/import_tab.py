"""
Import tab for the Financial Model GUI.
"""

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from src.database import get_session
from src.database_init import initialize_database
from src.services.bulk_import_service import BulkImportService
from src.services.ui_settings_service import UISettingsService


class ImportTab(ttk.Frame):
    """GUI for importing BMO and Nesbitt Burns Excel files."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)

        self.columnconfigure(1, weight=1)
        self.rowconfigure(8, weight=1)
        self._ui_settings = UISettingsService()

        # ---------------------------------------------------------
        # Title
        # ---------------------------------------------------------

        ttk.Label(
            self,
            text="Import Brokerage Data",
            font=("Segoe UI", 18, "bold"),
        ).grid(
            row=0,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(0, 25),
        )

        # ---------------------------------------------------------
        # BMO
        # ---------------------------------------------------------

        ttk.Label(
            self,
            text="BMO Directory:",
            font=("Segoe UI", 11),
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=(0, 10),
            pady=8,
        )

        self.bmo_directory = tk.StringVar(
            value=r"C:\Users\ronal\Downloads\bmo"
        )
        saved = self._ui_settings.get_screen("import")
        if isinstance(saved.get("bmo_directory"), str):
            self.bmo_directory.set(saved["bmo_directory"])

        ttk.Entry(
            self,
            textvariable=self.bmo_directory,
        ).grid(
            row=1,
            column=1,
            sticky="ew",
            pady=8,
        )

        ttk.Button(
            self,
            text="Browse...",
            command=self._browse_bmo,
        ).grid(
            row=1,
            column=2,
            padx=(10, 0),
            pady=8,
        )

        ttk.Button(
            self,
            text="Import BMO",
            command=self._import_bmo,
        ).grid(
            row=2,
            column=1,
            sticky="w",
            pady=(0, 15),
        )

        # ---------------------------------------------------------
        # Nesbitt Burns
        # ---------------------------------------------------------

        ttk.Label(
            self,
            text="Nesbitt Burns Directory:",
            font=("Segoe UI", 11),
        ).grid(
            row=3,
            column=0,
            sticky="w",
            padx=(0, 10),
            pady=8,
        )

        self.nesbitt_directory = tk.StringVar(
            value=r"C:\Users\ronal\Downloads\nesbitt"
        )
        if isinstance(saved.get("nesbitt_directory"), str):
            self.nesbitt_directory.set(saved["nesbitt_directory"])

        ttk.Entry(
            self,
            textvariable=self.nesbitt_directory,
        ).grid(
            row=3,
            column=1,
            sticky="ew",
            pady=8,
        )

        ttk.Button(
            self,
            text="Browse...",
            command=self._browse_nesbitt,
        ).grid(
            row=3,
            column=2,
            padx=(10, 0),
            pady=8,
        )

        ttk.Button(
            self,
            text="Import Nesbitt Burns",
            command=self._import_nesbitt,
        ).grid(
            row=4,
            column=1,
            sticky="w",
            pady=(0, 20),
        )

        # ---------------------------------------------------------
        # Re-import option
        # ---------------------------------------------------------

        self.force_reimport = tk.BooleanVar(
            value=bool(saved.get("force_reimport", False))
        )
        self.bmo_directory.trace_add("write", self._ui_setting_changed)
        self.nesbitt_directory.trace_add("write", self._ui_setting_changed)
        self.force_reimport.trace_add("write", self._ui_setting_changed)

        ttk.Checkbutton(
            self,
            text="Force re-import existing snapshots",
            variable=self.force_reimport,
        ).grid(
            row=5,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(0, 5),
        )

        ttk.Label(
            self,
            text=(
                "Use this after correcting an import. It replaces an "
                "existing snapshot even when the source timestamp is "
                "unchanged."
            ),
            wraplength=700,
        ).grid(
            row=6,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(0, 15),
        )

        # ---------------------------------------------------------
        # Results
        # ---------------------------------------------------------

        ttk.Label(
            self,
            text="Import Results",
            font=("Segoe UI", 13, "bold"),
        ).grid(
            row=7,
            column=0,
            columnspan=3,
            sticky="nw",
            pady=(10, 10),
        )

        results_frame = ttk.Frame(self)
        results_frame.grid(
            row=8,
            column=0,
            columnspan=3,
            sticky="nsew",
        )

        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)

        self.results_text = tk.Text(
            results_frame,
            height=15,
            wrap="word",
            state="disabled",
            font=("Consolas", 10),
        )

        self.results_text.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        scrollbar = ttk.Scrollbar(
            results_frame,
            orient="vertical",
            command=self.results_text.yview,
        )

        scrollbar.grid(
            row=0,
            column=1,
            sticky="ns",
        )

        self.results_text.configure(
            yscrollcommand=scrollbar.set
        )

        # Make the results area expand.
        self.rowconfigure(8, weight=1)

    # -------------------------------------------------------------
    # Directory selection
    # -------------------------------------------------------------

    def _browse_bmo(self) -> None:
        """Select the BMO directory."""

        directory = filedialog.askdirectory(
            title="Select BMO Directory",
            initialdir=self.bmo_directory.get(),
        )

        if directory:
            self.bmo_directory.set(directory)
            self._save_ui_settings()

    def _browse_nesbitt(self) -> None:
        """Select the Nesbitt Burns directory."""

        directory = filedialog.askdirectory(
            title="Select Nesbitt Burns Directory",
            initialdir=self.nesbitt_directory.get(),
        )

        if directory:
            self.nesbitt_directory.set(directory)
            self._save_ui_settings()

    def _ui_setting_changed(self, *_args) -> None:
        self._save_ui_settings()

    def _save_ui_settings(self) -> None:
        try:
            self._ui_settings.update(
                "import",
                {
                    "bmo_directory": self.bmo_directory.get(),
                    "nesbitt_directory": self.nesbitt_directory.get(),
                    "force_reimport": self.force_reimport.get(),
                },
            )
        except Exception:
            pass

    # -------------------------------------------------------------
    # Import operations
    # -------------------------------------------------------------

    def _import_bmo(self) -> None:
        """Import all BMO files in the selected directory."""

        self._import_directory(
            brokerage="BMO",
            directory=self.bmo_directory.get(),
        )

    def _import_nesbitt(self) -> None:
        """Import all Nesbitt Burns files in the selected directory."""

        self._import_directory(
            brokerage="Nesbitt Burns",
            directory=self.nesbitt_directory.get(),
        )

    def _import_directory(
        self,
        brokerage: str,
        directory: str,
    ) -> None:
        """Import all Excel files in a brokerage directory."""

        if not directory.strip():
            messagebox.showerror(
                "Import Error",
                f"Please select a {brokerage} directory.",
            )
            return

        directory_path = Path(directory)

        if not directory_path.exists():
            messagebox.showerror(
                "Import Error",
                f"Directory does not exist:\n\n{directory}",
            )
            return

        if not directory_path.is_dir():
            messagebox.showerror(
                "Import Error",
                f"Path is not a directory:\n\n{directory}",
            )
            return

        try:
            initialize_database()

            session = get_session()

            try:
                service = BulkImportService(session)

                if brokerage == "BMO":
                    result = service.import_bmo_directory(
                        directory_path,
                        force_reimport=self.force_reimport.get(),
                    )
                else:
                    result = service.import_nesbitt_directory(
                        directory_path,
                        force_reimport=self.force_reimport.get(),
                    )

            finally:
                session.close()

            self._display_result(
                brokerage=brokerage,
                directory=directory_path,
                result=result,
            )

        except Exception as exc:
            messagebox.showerror(
                "Import Error",
                f"Unable to import {brokerage} files:\n\n"
                f"{type(exc).__name__}: {exc}",
            )

    # -------------------------------------------------------------
    # Results
    # -------------------------------------------------------------

    def _display_result(
        self,
        brokerage: str,
        directory: Path,
        result,
    ) -> None:
        """Display the import results."""

        lines = [
            f"{brokerage} Import",
            "=" * 50,
            "",
            f"Directory: {directory}",
            f"Files found: {result.files_found}",
            f"Imported: {result.imported}",
            f"Replaced: {result.replaced}",
            f"Duplicates: {result.duplicates}",
            f"Errors: {result.errors}",
        ]

        if result.error_files:
            lines.extend(
                [
                    "",
                    "Files with errors:",
                ]
            )

            for error_file in result.error_files:
                lines.append(f"  {error_file}")

        lines.extend(
            [
                "",
                "=" * 50,
            ]
        )

        self._append_result("\n".join(lines))

    def _append_result(self, text: str) -> None:
        """Append text to the results window."""

        self.results_text.configure(state="normal")

        self.results_text.insert(
            "end",
            text + "\n\n",
        )

        self.results_text.see("end")

        self.results_text.configure(state="disabled")