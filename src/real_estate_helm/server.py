"""HTTP server for the early desktop/web client surface."""

from __future__ import annotations

import argparse
import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from real_estate_helm.api import ApiRouter
from real_estate_helm.repository import JsonDealRepository


def run_server(
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    data_dir: Path | str = ".real_estate_helm",
    static_dir: Path | str | None = None,
) -> ThreadingHTTPServer:
    static_root = Path(static_dir) if static_dir else Path(__file__).resolve().parents[2] / "web"
    router = ApiRouter(JsonDealRepository(data_dir))

    class Handler(RealEstateHelmHandler):
        pass

    Handler.api_router = router
    Handler.static_root = static_root

    server = ThreadingHTTPServer((host, port), Handler)
    server.serve_forever()
    return server


class RealEstateHelmHandler(BaseHTTPRequestHandler):
    api_router: ApiRouter
    static_root: Path

    def do_GET(self) -> None:
        if self.path.startswith("/api/"):
            self._handle_api("GET")
            return
        self._serve_static()

    def do_POST(self) -> None:
        if self.path.startswith("/api/"):
            self._handle_api("POST")
            return
        self._write_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _handle_api(self, method: str) -> None:
        body = self._read_json_body() if method == "POST" else None
        response = self.api_router.handle(method, self.path.removeprefix("/api"), body)
        self._write_json(HTTPStatus(response.status), response.body)

    def _read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("content-length", "0"))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _serve_static(self) -> None:
        relative = self.path.split("?", 1)[0].lstrip("/") or "index.html"
        path = (self.static_root / relative).resolve()
        try:
            path.relative_to(self.static_root.resolve())
        except ValueError:
            self._write_json(HTTPStatus.FORBIDDEN, {"error": "forbidden"})
            return
        if not path.exists() or not path.is_file():
            self._write_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _write_json(self, status: HTTPStatus, body: dict[str, Any] | list[Any]) -> None:
        data = json.dumps(body, indent=2, sort_keys=True, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="real-estate-helm-server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--data-dir", type=Path, default=Path(".real_estate_helm"))
    parser.add_argument("--static-dir", type=Path)
    args = parser.parse_args(argv)
    run_server(host=args.host, port=args.port, data_dir=args.data_dir, static_dir=args.static_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
