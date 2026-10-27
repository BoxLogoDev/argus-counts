"""콘솔 HTTP 서버. 표준 라이브러리 http.server만 사용한다.

GET /는 요청마다 새 시뮬레이션을 돌려 HTML로 보여 주고,
GET /api/report는 같은 시뮬레이션 리포트를 JSON으로 돌려준다.
"""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from terminal.simulator import run_simulation

from .render import render_html
from .view import build_view


def create_handler():
    class ConsoleHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/":
                body = render_html(build_view(run_simulation())).encode("utf-8")
                self._send(200, "text/html; charset=utf-8", body)
            elif path == "/api/report":
                body = json.dumps(
                    run_simulation(), ensure_ascii=False
                ).encode("utf-8")
                self._send(200, "application/json", body)
            else:
                self.send_error(404)

        def _send(self, status: int, content_type: str, body: bytes):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            return

    return ConsoleHandler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Argus console server")
    parser.add_argument("--host", default="127.0.0.1", help="바인드 주소")
    parser.add_argument("--port", type=int, default=8765, help="포트")
    args = parser.parse_args(argv)

    server = ThreadingHTTPServer((args.host, args.port), create_handler())
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
