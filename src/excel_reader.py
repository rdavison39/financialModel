"""
Simple Excel workbook reader.
"""

from pathlib import Path

from openpyxl import load_workbook
from openpyxl.workbook import Workbook


class ExcelReader:
    """Reads an Excel workbook."""

    def __init__(self, file_path: str | Path) -> None:
        """Initialize the reader with an Excel file path."""
        self.file_path = Path(file_path)

    def read(self) -> Workbook:
        """Open and return the Excel workbook."""
        if not self.file_path.exists():
            raise FileNotFoundError(
                f"Excel file not found: {self.file_path}"
            )

        return load_workbook(
            filename=self.file_path,
            data_only=True,
        )