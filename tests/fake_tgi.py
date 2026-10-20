"""Local stand-in for a Hugging Face TGI / OpenAI-compatible chat endpoint, used only by tests and demos."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from tests.conftest import valid_plan


class FakeTgi:
    def __init__(self, respond=None, port: int = 0) -> None:
        self.requests: list[dict] = []
        self.respond = respond or (lambda payload, n: json.dumps(valid_plan()))
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                length = int(self.headers.get("content-length", 0))
                payload = json.loads(self.rfile.read(length) or b"{}")
                outer.requests.append({"path": self.path, "auth": self.headers.get("authorization"), "payload": payload})
                try:
                    content = outer.respond(payload, len(outer.requests))
                    status, body = 200, {
                        "id": "x", "object": "chat.completion", "created": 0, "model": "fake",
                        "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": content}}],
                        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                    }
                except Exception as err:  # simulate provider failure
                    status, body = 500, {"error": str(err)}
                data = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):  # silence
                pass

        self.server = HTTPServer(("127.0.0.1", port), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self) -> "FakeTgi":
        self.thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self.server.shutdown()
        self.server.server_close()
