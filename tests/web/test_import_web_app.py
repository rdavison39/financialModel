"""
Unit tests for import_web_app.py.
"""

from __future__ import annotations

from src.web.import_web_app import (
    parse_uploaded_workbook,
    render_page,
    sanitize_filename,
)


def test_sanitize_filename_removes_path_and_unsafe_characters() -> None:
    """
    Uploaded filenames are reduced to safe local filenames.
    """

    assert (
        sanitize_filename("C:/Users/Ron/My Holdings 2026.xlsx")
        == "My_Holdings_2026.xlsx"
    )


def test_parse_uploaded_workbook_reads_multipart_file() -> None:
    """
    Multipart form data returns the uploaded workbook file.
    """

    boundary = "----boundary"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="workbook"; '
        'filename="holdings.xlsx"\r\n'
        "Content-Type: application/vnd.openxmlformats-officedocument."
        "spreadsheetml.sheet\r\n"
        "\r\n"
        "workbook-bytes\r\n"
        f"--{boundary}--\r\n"
    ).encode("utf-8")

    upload = parse_uploaded_workbook(
        f"multipart/form-data; boundary={boundary}",
        body,
    )

    assert upload.filename == "holdings.xlsx"
    assert upload.content == b"workbook-bytes"


def test_render_page_escapes_result_text() -> None:
    """
    Rendered result text is escaped before entering HTML.
    """

    html = render_page(
        status="Done",
        result="<script>alert('x')</script>",
    )

    assert "<script>" not in html
    assert "&lt;script&gt;" in html
