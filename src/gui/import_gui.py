"""
import_gui.py

Small Tkinter GUI for importing a BMO InvestorLine workbook.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from traceback import format_exc

from src.config.settings import settings
from src.database.database import database
from src.services.bmo_workbook_import_runner import (
    import_bmo_workbook,
)
from src.services.import_result import ImportResult
from src.services.import_result_formatter import format_import_result


class ImportGui:
    """
    Tkinter application for importing one workbook.
    """

    def __init__(
        self,
        root: tk.Tk,
    ) -> None:
        """
        Initialize the GUI.

        Args:
            root:
                Tk root window.
        """

        self._root = root
        self._selected_file: Path | None = None

        self._file_var = tk.StringVar(value="No file selected")
        self._status_var = tk.StringVar(value="Ready")

        self._build_window()

    def _build_window(self) -> None:
        """
        Build the window layout.
        """

        self._root.title("Davison Financial Model - BMO Import")
        self._root.geometry("760x520")
        self._root.minsize(680, 460)

        frame = ttk.Frame(
            self._root,
            padding=16,
        )
        frame.pack(
            fill=tk.BOTH,
            expand=True,
        )

        file_row = ttk.Frame(frame)
        file_row.pack(
            fill=tk.X,
            pady=(0, 12),
        )

        ttk.Button(
            file_row,
            text="Choose Workbook",
            command=self._choose_file,
        ).pack(
            side=tk.LEFT,
        )

        ttk.Label(
            file_row,
            textvariable=self._file_var,
        ).pack(
            side=tk.LEFT,
            fill=tk.X,
            expand=True,
            padx=(12, 0),
        )

        action_row = ttk.Frame(frame)
        action_row.pack(
            fill=tk.X,
            pady=(0, 12),
        )

        ttk.Button(
            action_row,
            text="Import",
            command=self._import_selected_file,
        ).pack(
            side=tk.LEFT,
        )

        ttk.Button(
            action_row,
            text="Clear Output",
            command=self._clear_output,
        ).pack(
            side=tk.LEFT,
            padx=(8, 0),
        )

        ttk.Label(
            action_row,
            textvariable=self._status_var,
        ).pack(
            side=tk.RIGHT,
        )

        self._output = tk.Text(
            frame,
            wrap=tk.WORD,
            height=20,
            padx=6,
            pady=6,
            relief=tk.SOLID,
            bd=1,
        )
        self._output.pack(
            fill=tk.BOTH,
            expand=True,
        )

        self._output.bind("<Control-c>", self._copy_selection)
        self._output.bind("<Control-C>", self._copy_selection)
        self._output.bind("<Button-3>", self._show_context_menu)
        self._output.bind("<Key>", self._handle_output_key)

        self._write_output(
            "Select a BMO InvestorLine workbook, then click Import.\n"
            f"Database: {settings.database_file}\n"
        )

    def _choose_file(self) -> None:
        """
        Ask the user to select a workbook.
        """

        filename = filedialog.askopenfilename(
            title="Choose BMO InvestorLine workbook",
            filetypes=(
                ("Excel workbooks", "*.xlsx *.xlsm"),
                ("All files", "*.*"),
            ),
        )

        if not filename:
            return

        self._selected_file = Path(filename)
        self._file_var.set(str(self._selected_file))
        self._status_var.set("Workbook selected")

    def _import_selected_file(self) -> None:
        """
        Import the selected workbook.
        """

        if self._selected_file is None:
            messagebox.showwarning(
                "No workbook selected",
                "Choose a BMO InvestorLine workbook first.",
            )
            return

        self._status_var.set("Importing...")
        self._root.update_idletasks()

        database.create_database()

        session = database.get_session()

        try:
            result = import_bmo_workbook(
                self._selected_file,
                session,
            )

            self._write_output(
                "\n" + self._format_result(result) + "\n"
            )
            self._status_var.set("Import complete")

        except Exception as exc:
            session.rollback()
            self._write_output(
                "\nImport failed.\n"
                f"{exc}\n\n"
                f"{format_exc()}\n"
            )
            self._status_var.set("Import failed")

        finally:
            session.close()

    def _format_result(
        self,
        result: ImportResult,
    ) -> str:
        """
        Format an ImportResult for display.
        """

        return format_import_result(result)

    def _handle_output_key(self, event: tk.Event) -> str | None:
        """
        Prevent editing the output text while allowing copy shortcuts.
        """

        if event.keysym in {"c", "C"} and event.state & 0x4:
            self._copy_selection(event)
            return "break"

        if event.keysym in {"a", "A"} and event.state & 0x4:
            self._select_all_output()
            return "break"

        return "break"

    def _show_context_menu(self, event: tk.Event) -> None:
        """
        Show a context menu for copying or selecting output text.
        """

        menu = tk.Menu(self._output, tearoff=0)
        menu.add_command(label="Copy", command=self._copy_selection)
        menu.add_command(label="Select All", command=self._select_all_output)
        menu.add_separator()
        menu.add_command(label="Clear", command=self._clear_output)
        menu.post(event.x_root, event.y_root)

    def _copy_selection(self, _event: tk.Event | None = None) -> None:
        """
        Copy any currently selected text to the clipboard.
        """

        try:
            selected = self._output.get(tk.SEL_FIRST, tk.SEL_LAST)
        except tk.TclError:
            selected = ""

        if selected:
            self._output.clipboard_clear()
            self._output.clipboard_append(selected)

    def _select_all_output(self) -> None:
        """
        Select all output text.
        """

        self._output.tag_add(tk.SEL, "1.0", tk.END)
        self._output.mark_set(tk.INSERT, tk.END)
        self._output.see(tk.INSERT)

    def _clear_output(self) -> None:
        """
        Clear the output text.
        """

        self._output.delete("1.0", tk.END)

    def _write_output(
        self,
        message: str,
    ) -> None:
        """
        Append text to the output area.
        """

        self._output.insert(tk.END, message)
        self._output.see(tk.END)


def main() -> None:
    """
    Run the BMO import GUI.
    """

    root = tk.Tk()
    app = ImportGui(root)

    def close() -> None:
        database.close()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", close)
    root.mainloop()

    _ = app


if __name__ == "__main__":
    main()
