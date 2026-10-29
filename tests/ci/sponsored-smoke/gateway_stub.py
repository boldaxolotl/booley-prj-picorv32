#!/usr/bin/env python3
"""Stub model gateway for the sponsored-mode CI smoke test.

The sponsored Codespaces config sends Codex traffic to the demo gateway with a
bearer token. CI must not use the real gateway or any real credential, so this
stub stands in for it. It speaks just enough of the OpenAI Responses API for
one Codex turn:

- ``POST <base>/responses`` with the expected bearer token answers a canned
  server-sent-event stream whose assistant message is ``REPLY_TEXT``.
- The same request with a missing or wrong token gets HTTP 401.
- Anything else gets HTTP 404 (Codex tolerates a 404 from ``GET /models``).

Every request is appended to a JSON-lines log so the workflow can assert that
a Codex request reached the stub. The log never holds the token, headers or
request content: only the method, path, whether the token matched, and the
requested model.

The gateway policy accepts only ``https://`` URLs, so the stub serves TLS.
``make-certs`` writes a throwaway CA and a server certificate for the given
host name; the CA is what the container trusts. Standard library plus the
``openssl`` CLI only, so it runs on a bare CI runner.

Usage:
    gateway_stub.py make-certs --dir DIR --host NAME
    gateway_stub.py serve --dir DIR --port PORT --token-file FILE --log FILE
"""

from __future__ import annotations

import argparse
import hmac
import json
import ssl
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# The assistant text of every canned reply; the smoke test looks for it in
# Codex's output to prove the reply came from this stub.
REPLY_TEXT = "BOOLEY-GATEWAY-STUB-OK"

# Codex appends "/responses" to the configured base URL (".../v1").
RESPONSES_SUFFIX = "/responses"

CA_CERT = "ca.pem"
CA_KEY = "ca.key"
SERVER_CERT = "server.pem"
SERVER_KEY = "server.key"


def _openssl(*args: str) -> None:
    """Run one openssl command, failing loudly with its stderr."""
    subprocess.run(
        ["openssl", *args], check=True, capture_output=True, text=True, timeout=60
    )


def make_certs(cert_dir: Path, host: str) -> None:
    """Write a throwaway CA and a server certificate for *host* into *cert_dir*.

    A separate CA (rather than one self-signed server certificate) matters:
    rustls, which Codex uses, rejects a CA certificate presented as the server
    certificate.
    """
    cert_dir.mkdir(parents=True, exist_ok=True)
    ca_cert, ca_key = cert_dir / CA_CERT, cert_dir / CA_KEY
    server_cert, server_key = cert_dir / SERVER_CERT, cert_dir / SERVER_KEY
    csr = cert_dir / "server.csr"
    extensions = cert_dir / "server.ext"
    _openssl(
        "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "2",
        "-subj", "/CN=Booley gateway stub CA",
        "-addext", "basicConstraints=critical,CA:TRUE",
        "-addext", "keyUsage=critical,keyCertSign,cRLSign",
        "-keyout", str(ca_key), "-out", str(ca_cert),
    )  # fmt: skip
    _openssl(
        "req", "-newkey", "rsa:2048", "-nodes", "-subj", f"/CN={host}",
        "-keyout", str(server_key), "-out", str(csr),
    )  # fmt: skip
    extensions.write_text(
        "basicConstraints=critical,CA:FALSE\n"
        "keyUsage=critical,digitalSignature,keyEncipherment\n"
        "extendedKeyUsage=serverAuth\n"
        f"subjectAltName=DNS:{host}\n",
        encoding="utf-8",
    )
    _openssl(
        "x509", "-req", "-in", str(csr), "-days", "2",
        "-CA", str(ca_cert), "-CAkey", str(ca_key), "-CAcreateserial",
        "-extfile", str(extensions), "-out", str(server_cert),
    )  # fmt: skip
    # Only the CA certificate leaves this directory; keys stay private.
    for key in (ca_key, server_key):
        key.chmod(0o600)


def _sse_event(payload: dict[str, object]) -> bytes:
    """Encode one server-sent event the way the Responses API streams it."""
    return f"event: {payload['type']}\ndata: {json.dumps(payload)}\n\n".encode()


def canned_stream(response_id: str) -> bytes:
    """Return a complete Responses stream: one assistant message, then completion."""
    message = {
        "type": "message",
        "role": "assistant",
        "id": f"msg_{response_id}",
        "content": [{"type": "output_text", "text": REPLY_TEXT}],
    }
    usage = {
        "input_tokens": 1,
        "input_tokens_details": {"cached_tokens": 0},
        "output_tokens": 1,
        "output_tokens_details": {"reasoning_tokens": 0},
        "total_tokens": 2,
    }
    events = (
        {"type": "response.created", "response": {"id": response_id}},
        {"type": "response.output_item.done", "output_index": 0, "item": message},
        {"type": "response.completed", "response": {"id": response_id, "usage": usage}},
    )
    return b"".join(_sse_event(event) for event in events)


class _StubState:
    """Shared, thread-safe state: the expected token, the log, a request counter."""

    def __init__(self, token: str, log_path: Path) -> None:
        self.token = token
        self.log_path = log_path
        self._lock = threading.Lock()
        self._count = 0

    def record(self, entry: dict[str, object]) -> int:
        """Append *entry* to the log and return this request's sequence number."""
        with self._lock:
            self._count += 1
            entry = {"seq": self._count, **entry}
            with self.log_path.open("a", encoding="utf-8") as log:
                log.write(json.dumps(entry, sort_keys=True) + "\n")
            return self._count


def _handler_for(state: _StubState) -> type[BaseHTTPRequestHandler]:
    """Build a request handler class bound to *state*."""

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, format: str, *args: object) -> None:
            """Silence the default per-request stderr line; the JSON log covers it."""

        def _authorized(self) -> bool:
            presented = self.headers.get("Authorization", "")
            expected = f"Bearer {state.token}"
            return hmac.compare_digest(presented.encode(), expected.encode())

        def _reply(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _read_json_body(self) -> dict[str, object]:
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            try:
                body = json.loads(raw or b"{}")
            except ValueError:
                return {}
            return body if isinstance(body, dict) else {}

        def do_GET(self) -> None:
            state.record(
                {"method": "GET", "path": self.path, "authorized": self._authorized()}
            )
            self._reply(404, b'{"error":"not found"}', "application/json")

        def do_POST(self) -> None:
            body = self._read_json_body()
            authorized = self._authorized()
            is_responses = self.path.rstrip("/").endswith(RESPONSES_SUFFIX)
            seq = state.record(
                {
                    "method": "POST",
                    "path": self.path,
                    "authorized": authorized,
                    "model": body.get("model"),
                }
            )
            if not is_responses:
                self._reply(404, b'{"error":"not found"}', "application/json")
            elif not authorized:
                self._reply(
                    401, b'{"error":"invalid gateway token"}', "application/json"
                )
            else:
                self._reply(200, canned_stream(f"resp_stub_{seq}"), "text/event-stream")

    return Handler


def build_server(
    cert_dir: Path, port: int, token: str, log_path: Path, host: str = "0.0.0.0"
) -> ThreadingHTTPServer:
    """Return a TLS stub server bound to *host*:*port* (0 picks a free port)."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.touch()
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_dir / SERVER_CERT, cert_dir / SERVER_KEY)
    server = ThreadingHTTPServer(
        (host, port), _handler_for(_StubState(token, log_path))
    )
    server.socket = context.wrap_socket(server.socket, server_side=True)
    return server


def serve(cert_dir: Path, port: int, token_file: Path, log_path: Path) -> None:
    """Serve the stub over TLS on all interfaces until interrupted.

    All interfaces, because the container reaches the stub through the Docker
    host gateway address, not the runner's loopback.
    """
    token = token_file.read_text(encoding="utf-8").strip()
    if not token:
        raise SystemExit(f"gateway stub: {token_file} holds no token")
    server = build_server(cert_dir, port, token, log_path)
    print(f"gateway stub listening on :{port}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    certs = commands.add_parser(
        "make-certs", help="write a throwaway CA and server certificate"
    )
    certs.add_argument("--dir", type=Path, required=True)
    certs.add_argument("--host", required=True)
    serve_parser = commands.add_parser("serve", help="serve the stub over TLS")
    serve_parser.add_argument(
        "--dir", type=Path, required=True, help="directory from make-certs"
    )
    serve_parser.add_argument("--port", type=int, required=True)
    serve_parser.add_argument("--token-file", type=Path, required=True)
    serve_parser.add_argument("--log", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "make-certs":
        make_certs(args.dir, args.host)
    else:
        serve(args.dir, args.port, args.token_file, args.log)
    return 0


if __name__ == "__main__":
    sys.exit(main())
