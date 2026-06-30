"""
import_web_app.py

Local web interface for importing BMO InvestorLine workbooks.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from email import policy
from email.parser import BytesParser
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from traceback import format_exc
from urllib.parse import parse_qs, urlparse

from src.config.settings import settings
from src.database.database import database
from src.services.bmo_workbook_import_runner import (
    import_bmo_workbook,
)
from src.services.import_result_formatter import format_import_result

HOST = "127.0.0.1"
PORT = 8000
MAX_UPLOAD_BYTES = 20 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class UploadedWorkbook:
    """
    Workbook uploaded through the web form.
    """

    filename: str
    content: bytes


def sanitize_filename(
    filename: str,
) -> str:
    """
    Return a conservative local filename for an upload.
    """

    cleaned = Path(filename).name.strip()
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", cleaned)

    if not cleaned:
        return "uploaded_workbook.xlsx"

    return cleaned


def parse_uploaded_workbook(
    content_type: str,
    body: bytes,
) -> UploadedWorkbook:
    """
    Parse a multipart form upload and return the workbook file.
    """

    if "multipart/form-data" not in content_type:
        raise ValueError("Expected multipart form data.")

    message = BytesParser(policy=policy.default).parsebytes(
        b"Content-Type: "
        + content_type.encode("utf-8")
        + b"\r\nMIME-Version: 1.0\r\n\r\n"
        + body
    )

    for part in message.iter_parts():
        if part.get_content_disposition() != "form-data":
            continue

        if part.get_param("name", header="content-disposition") != (
            "workbook"
        ):
            continue

        filename = part.get_filename()

        if not filename:
            raise ValueError("No workbook file was selected.")

        content = part.get_payload(decode=True)

        if not content:
            raise ValueError("Uploaded workbook is empty.")

        return UploadedWorkbook(
            filename=sanitize_filename(filename),
            content=content,
        )

    raise ValueError("Upload did not include a workbook file.")


def save_uploaded_workbook(
    upload: UploadedWorkbook,
) -> Path:
    """
    Save an uploaded workbook and return its local path.
    """

    upload_folder = settings.data_folder / "uploads"
    upload_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = upload_folder / upload.filename
    path.write_bytes(upload.content)

    return path


class ImportWebHandler(BaseHTTPRequestHandler):
    """
    HTTP handler for the local import web UI.
    """

    server_version = "DavisonFinancialModel/0.1"

    def do_GET(self) -> None:
        """
        Render the upload page.
        """

        parsed = urlparse(self.path)

        if parsed.path != "/":
            self._send_not_found()
            return

        query = parse_qs(parsed.query)

        self._send_html(
            render_page(
                status=query.get("status", ["Ready"])[0],
                result=query.get("result", [""])[0],
                error=query.get("error", [""])[0],
            )
        )

    def do_POST(self) -> None:
        """
        Handle workbook uploads.
        """

        if self.path != "/import":
            self._send_not_found()
            return

        try:
            content_length = int(
                self.headers.get("Content-Length", "0")
            )

            if content_length <= 0:
                raise ValueError("No upload body was received.")

            if content_length > MAX_UPLOAD_BYTES:
                raise ValueError("Uploaded workbook is too large.")

            body = self.rfile.read(content_length)
            upload = parse_uploaded_workbook(
                self.headers.get("Content-Type", ""),
                body,
            )
            workbook_path = save_uploaded_workbook(upload)

            database.create_database()
            session = database.get_session()

            try:
                result = import_bmo_workbook(
                    workbook_path,
                    session,
                )
            finally:
                session.close()

            self._send_html(
                render_page(
                    status="Import complete",
                    result=format_import_result(result),
                    filename=upload.filename,
                )
            )

        except Exception as exc:
            self._send_html(
                render_page(
                    status="Import failed",
                    error=f"{exc}\n\n{format_exc()}",
                ),
                status=HTTPStatus.BAD_REQUEST,
            )

    def log_message(
        self,
        format: str,
        *args: object,
    ) -> None:
        """
        Silence default request logging.
        """

    def _send_html(
        self,
        html: str,
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        """
        Send an HTML response.
        """

        encoded = html.encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_not_found(self) -> None:
        """
        Send a not-found response.
        """

        self._send_html(
            render_page(
                status="Not found",
                error="The requested page was not found.",
            ),
            status=HTTPStatus.NOT_FOUND,
        )


def render_page(
    *,
    status: str,
    result: str = "",
    error: str = "",
    filename: str = "",
) -> str:
    """
    Render the import page.
    """

    result_html = ""

    if result:
        result_html = (
            '<section class="panel success">'
            "<h2>Import Result</h2>"
            f"<pre>{escape(result)}</pre>"
            "</section>"
        )

    error_html = ""

    if error:
        error_html = (
            '<section class="panel error">'
            "<h2>Error</h2>"
            f"<pre>{escape(error)}</pre>"
            "</section>"
        )

    filename_html = ""

    if filename:
        filename_html = (
            f'<p class="filename">Uploaded: {escape(filename)}</p>'
        )

    return f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Davison Financial Model</title>
    <style>
        :root {{
            color-scheme: light;
            --bg: #f7f7f4;
            --ink: #202124;
            --muted: #5f6368;
            --line: #d8d8d2;
            --panel: #ffffff;
            --accent: #1f6f5f;
            --accent-dark: #174f45;
            --success: #eaf5ef;
            --error: #fff0f0;
        }}

        * {{
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            min-height: 100vh;
            background: var(--bg);
            color: var(--ink);
            font-family: "Segoe UI", Arial, sans-serif;
        }}

        main {{
            width: min(920px, calc(100vw - 32px));
            margin: 0 auto;
            padding: 32px 0;
        }}

        header {{
            display: flex;
            align-items: flex-end;
            justify-content: space-between;
            gap: 16px;
            margin-bottom: 20px;
            border-bottom: 1px solid var(--line);
            padding-bottom: 16px;
        }}

        h1 {{
            margin: 0;
            font-size: 30px;
            font-weight: 650;
        }}

        .status {{
            color: var(--muted);
            font-size: 14px;
            white-space: nowrap;
        }}

        .panel {{
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 18px;
            margin-bottom: 16px;
        }}

        .panel h2 {{
            margin: 0 0 12px;
            font-size: 17px;
        }}

        form {{
            display: grid;
            grid-template-columns: 1fr auto;
            gap: 12px;
            align-items: center;
        }}

        input[type="file"] {{
            width: 100%;
            border: 1px solid var(--line);
            border-radius: 6px;
            padding: 10px;
            background: #fbfbf9;
        }}

        button {{
            border: 0;
            border-radius: 6px;
            background: var(--accent);
            color: white;
            padding: 11px 18px;
            font-weight: 650;
            cursor: pointer;
        }}

        button:hover {{
            background: var(--accent-dark);
        }}

        pre {{
            margin: 0;
            white-space: pre-wrap;
            overflow-wrap: anywhere;
            font-family: Consolas, "Courier New", monospace;
            font-size: 14px;
            line-height: 1.45;
        }}

        .success {{
            background: var(--success);
        }}

        .error {{
            background: var(--error);
        }}

        .filename {{
            margin: 12px 0 0;
            color: var(--muted);
        }}

        @media (max-width: 640px) {{
            header {{
                display: block;
            }}

            .status {{
                margin-top: 8px;
                white-space: normal;
            }}

            form {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <main>
        <header>
            <h1>Davison Financial Model</h1>
            <div class="status">{escape(status)}</div>
        </header>

        <section class="panel">
            <h2>BMO InvestorLine Import</h2>
            <form method="post" action="/import"
                  enctype="multipart/form-data">
                <input type="file" name="workbook"
                       accept=".xlsx,.xlsm" required>
                <button type="submit">Import Workbook</button>
            </form>
            {filename_html}
        </section>

        {result_html}
        {error_html}
    </main>
</body>
</html>
"""


def run_server(
    host: str = HOST,
    port: int = PORT,
) -> None:
    """
    Run the local web server.
    """

    server = ThreadingHTTPServer(
        (host, port),
        ImportWebHandler,
    )

    print(f"Serving Davison Financial Model at http://{host}:{port}")

    try:
        server.serve_forever()
    finally:
        database.close()
        server.server_close()


def main() -> None:
    """
    Start the web import application.
    """

    run_server()


if __name__ == "__main__":
    main()
