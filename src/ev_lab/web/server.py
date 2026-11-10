"""HTTP front for `TrainerApp`: the standard library's server, bound to this machine only."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from ev_lab.web.app import ApiError, TrainerApp

HOST = "127.0.0.1"  # loopback only: the page is never reachable from another machine
INDEX = Path(__file__).parent / "static" / "index.html"
MAX_BODY = 10_000  # bytes; every request is a few short fields


def respond(app: TrainerApp, method: str, path: str, raw_body: bytes) -> tuple[int, str, bytes]:
    """(status, content type, body) for one request. Pure: no sockets involved."""
    if method == "GET" and path in ("/", "/index.html"):
        return HTTPStatus.OK, "text/html; charset=utf-8", INDEX.read_bytes()
    if method == "GET" and path.startswith("/figures/"):
        figure = app.figure_path(path.removeprefix("/figures/"))
        if figure is None:
            return HTTPStatus.NOT_FOUND, "application/json", b'{"error": "no such figure"}'
        return HTTPStatus.OK, "image/png", figure.read_bytes()
    try:
        body: Any = json.loads(raw_body) if raw_body.strip() else {}
        if not isinstance(body, dict):
            raise ApiError("the request body must be a JSON object")
        result = app.handle(method, path, body)
        return HTTPStatus.OK, "application/json", json.dumps(result).encode()
    except json.JSONDecodeError:
        return _error(HTTPStatus.BAD_REQUEST, "the request body is not valid JSON")
    except ApiError as e:
        return _error(HTTPStatus.BAD_REQUEST, str(e))
    except KeyError:
        return _error(HTTPStatus.NOT_FOUND, f"no route {method} {path}")


def _error(status: HTTPStatus, message: str) -> tuple[int, str, bytes]:
    return status, "application/json", json.dumps({"error": message}).encode()


def make_handler(app: TrainerApp) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def _serve(self, method: str) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                status, kind, payload = _error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "too large")
            else:
                raw = self.rfile.read(length) if length else b""
                status, kind, payload = respond(app, method, self.path.split("?")[0], raw)
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:
            self._serve("GET")

        def do_POST(self) -> None:
            self._serve("POST")

        def log_message(self, format: str, *args: Any) -> None:
            app.ctx.logger.debug("web %s", format % args)

    return Handler


def serve(app: TrainerApp, port: int) -> HTTPServer:
    """A server ready for `serve_forever()`; single-threaded on purpose (one user)."""
    return HTTPServer((HOST, port), make_handler(app))
