"""
import_web_app.py

Local web interface for importing BMO InvestorLine workbooks.

Author:
    Ron Davison / ChatGPT
"""

# ruff: noqa: E501

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
from src.database.unit_of_work import UnitOfWork
from src.services.bmo_workbook_import_runner import (
    import_bmo_workbook,
)
from src.services.import_result_formatter import format_import_result
from src.services.portfolio_dashboard_service import (
    PortfolioDashboard,
    PortfolioDashboardService,
)

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

        if parsed.path == "/portfolio":
            self._send_portfolio()
            return

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

    def _send_portfolio(self) -> None:
        """Render the read-only holdings dashboard."""

        database.create_database()
        session = database.get_session()

        try:
            dashboard = PortfolioDashboardService(
                UnitOfWork(session)
            ).build()
            self._send_html(render_portfolio_page(dashboard))
        finally:
            session.close()


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

        <p><a href="/portfolio">View portfolio dashboard</a></p>

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


def render_portfolio_page(
    dashboard: PortfolioDashboard,
) -> str:
    """Render the BMO holdings dashboard from statement snapshot values."""

    if not dashboard.holdings:
        content = (
            "<section class=\"panel\"><h2>No BMO holdings yet</h2>"
            "<p>Import a BMO InvestorLine workbook first.</p></section>"
        )
    else:
        rows = "".join(
            "<tr>"
            f"<td>{escape(holding.ticker)}</td>"
            f"<td>{escape(holding.company_name)}</td>"
            f"<td>{holding.shares:,.4f}</td>"
            f"<td>{_currency(holding.book_cost)}</td>"
            f"<td>{_currency(holding.statement_value)}</td>"
            f"<td class=\"{'gain' if holding.unrealized_gain >= 0 else 'loss'}\">"
            f"{_currency(holding.unrealized_gain)}</td></tr>"
            for holding in dashboard.holdings
        )
        content = f"""
        <section class="cards">
            <article><span>Statement value</span><strong>{_currency(dashboard.statement_value)}</strong></article>
            <article><span>Book cost</span><strong>{_currency(dashboard.book_cost)}</strong></article>
            <article><span>Unrealized gain/loss</span><strong class="{'gain' if dashboard.unrealized_gain >= 0 else 'loss'}">{_currency(dashboard.unrealized_gain)}</strong></article>
            <article><span>CAD cash</span><strong>{_currency(dashboard.cash_value)}</strong></article>
        </section>
        <section class="panel"><h2>Portfolio value by import</h2>{_chart(dashboard)}</section>
        <section class="panel"><h2>Equity holdings</h2>
        <table><thead><tr><th>Ticker</th><th>Company</th><th>Shares</th><th>Book cost</th><th>Statement value</th><th>Unrealized gain/loss</th></tr></thead>
        <tbody>{rows}</tbody></table></section>
        """

    imported_on = (
        dashboard.imported_on.isoformat()
        if dashboard.imported_on is not None
        else "No imports"
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Portfolio dashboard</title><style>
body{{margin:0;background:#f7f7f4;color:#202124;font-family:"Segoe UI",Arial,sans-serif}}main{{width:min(1200px,calc(100vw - 32px));margin:auto;padding:32px 0}}header{{display:flex;justify-content:space-between;align-items:end;border-bottom:1px solid #d8d8d2;padding-bottom:16px}}h1{{margin:0}}a{{color:#1f6f5f;font-weight:650}}.muted,span{{color:#5f6368}}.panel,.cards article{{background:white;border:1px solid #d8d8d2;border-radius:8px;padding:18px;margin:16px 0}}.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:16px}}.cards article{{margin:0}}.cards strong{{display:block;font-size:24px;margin-top:8px}}table{{width:100%;border-collapse:collapse}}th,td{{padding:10px;text-align:left;border-bottom:1px solid #d8d8d2}}th{{color:#5f6368}}.gain{{color:#157347}}.loss{{color:#b42318}}svg{{width:100%;height:260px}}@media(max-width:760px){{.cards{{grid-template-columns:repeat(2,1fr)}}table{{font-size:12px}}}}
</style></head><body><main><header><div><h1>BMO Equity Portfolio</h1><p class="muted">Latest imported statement: {imported_on}</p></div><a href="/">Import workbook</a></header>{content}<p class="muted">Values are from imported BMO statements. Live Yahoo pricing and daily valuation refresh are the next iteration.</p></main></body></html>"""


def _currency(value: object) -> str:
    """Format a Decimal financial amount as Canadian currency."""

    return f"${value:,.2f} CAD"


def _chart(dashboard: PortfolioDashboard) -> str:
    """Render a compact SVG chart of values recorded at import time."""

    points = dashboard.history
    if len(points) < 2:
        return "<p class=\"muted\">Import another later statement to begin the chart.</p>"

    values = [point.value for point in points]
    low, high = min(values), max(values)
    span = high - low or 1
    width, height, padding = 1000, 220, 24
    coordinates = " ".join(
        f"{padding + index * (width - 2 * padding) / (len(points) - 1):.1f},"
        f"{height - padding - float((point.value - low) / span) * (height - 2 * padding):.1f}"
        for index, point in enumerate(points)
    )
    return f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Portfolio value history"><line x1="{padding}" y1="{height-padding}" x2="{width-padding}" y2="{height-padding}" stroke="#d8d8d2"/><polyline points="{coordinates}" fill="none" stroke="#1f6f5f" stroke-width="4"/></svg>'


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
