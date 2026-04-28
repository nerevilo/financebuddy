"""Tiny localhost HTTP server for Teller Connect enrollment capture."""
from __future__ import annotations

import json
import os
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from . import db
from .link_bank import link

HERE = Path(__file__).resolve().parent
PAGE = HERE / "connect.html"
PORT = 8787


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path in ("/", "/connect", "/connect.html"):
            html = PAGE.read_text(encoding="utf-8").replace(
                "{{TELLER_APP_ID}}", os.environ.get("TELLER_APP_ID", "")
            ).replace(
                "{{TELLER_ENV}}", os.environ.get("TELLER_ENV", "development")
            )
            self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
            return
        if self.path == "/institutions":
            with db.cursor() as conn:
                rows = [dict(r) for r in conn.execute(
                    "SELECT id, name, last_synced_at FROM institutions"
                ).fetchall()]
            self._send(200, json.dumps(rows).encode(), "application/json")
            return
        self._send(404, b"not found", "text/plain")

    def do_POST(self) -> None:
        if self.path != "/link":
            self._send(404, b"not found", "text/plain")
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode())
            link(payload["id"], payload["name"], payload["token"])
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self._send(400, json.dumps({"error": str(e)}).encode(), "application/json")
            return
        self._send(200, json.dumps({"ok": True}).encode(), "application/json")

    def log_message(self, fmt, *args):
        print(f"[connect] {fmt % args}")


def main() -> None:
    db.init()
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://localhost:{PORT}/"
    print(f"Serving Teller Connect at {url}  (Ctrl-C to stop)")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
