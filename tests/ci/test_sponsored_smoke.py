"""Unit tests for the sponsored-mode smoke: the gateway stub and the run verdict."""

from __future__ import annotations

import http.client
import importlib.util
import json
import shutil
import ssl
import threading
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from typing import NamedTuple

import pytest

SMOKE_DIR = Path(__file__).parent / "sponsored-smoke"
TOKEN = "stub-test-token-0123456789"


def _load(name: str) -> ModuleType:
    """Import a script from the sponsored-smoke directory (its name has a hyphen)."""
    spec = importlib.util.spec_from_file_location(name, SMOKE_DIR / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


stub = _load("gateway_stub")
run_smoke = _load("run_smoke")


def _sse_events(stream: bytes) -> list[dict[str, object]]:
    """Parse a server-sent-event stream into its JSON payloads, checking event names."""
    events = []
    for block in stream.decode().strip().split("\n\n"):
        name_line, data_line = block.split("\n")
        payload = json.loads(data_line.removeprefix("data: "))
        assert name_line == f"event: {payload['type']}"
        events.append(payload)
    return events


def test_canned_stream_is_one_message_then_completion() -> None:
    events = _sse_events(stub.canned_stream("resp_x"))

    assert [event["type"] for event in events] == [
        "response.created",
        "response.output_item.done",
        "response.completed",
    ]
    message = events[1]["item"]
    assert message["role"] == "assistant"
    assert message["content"] == [{"type": "output_text", "text": stub.REPLY_TEXT}]
    assert events[2]["response"]["id"] == "resp_x"
    assert events[2]["response"]["usage"]["total_tokens"] == 2


def test_smoke_script_expects_the_stub_reply_text() -> None:
    assert f"stub_reply={stub.REPLY_TEXT}\n" in (SMOKE_DIR / "smoke.sh").read_text()


class StubServer(NamedTuple):
    """A running stub: its loopback port, the CA to trust, and its request log."""

    port: int
    ca: Path
    log: Path


@pytest.fixture(scope="module")
def stub_server(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[StubServer]:
    """Serve the stub on a free loopback port; yield (port, CA file, request log)."""
    # Fail rather than skip: a skipped stub suite would leave the CI gate green.
    assert shutil.which("openssl"), "the stub tests need the openssl CLI"
    root = tmp_path_factory.mktemp("stub")
    certs = root / "certs"
    stub.make_certs(certs, "localhost")
    log = root / "requests.jsonl"
    server = stub.build_server(certs, 0, TOKEN, log, host="127.0.0.1")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield StubServer(server.server_address[1], certs / stub.CA_CERT, log)
    server.shutdown()
    server.server_close()


def _request(
    server: StubServer, method: str, path: str, token: str | None
) -> tuple[int, str, bytes]:
    """Send one request over TLS verified against the stub CA; return status, type, body."""
    context = ssl.create_default_context(cafile=str(server.ca))
    connection = http.client.HTTPSConnection(
        "localhost", server.port, context=context, timeout=10
    )
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    body = (
        json.dumps({"model": "gpt-6-luna", "input": "secret prompt"})
        if method == "POST"
        else None
    )
    connection.request(method, path, body=body, headers=headers)
    response = connection.getresponse()
    result = (
        response.status,
        response.getheader("Content-Type") or "",
        response.read(),
    )
    connection.close()
    return result


def _log_entries(server: StubServer) -> list[dict[str, object]]:
    return [json.loads(line) for line in server.log.read_text().splitlines()]


def test_stub_streams_the_canned_reply_for_the_expected_token(
    stub_server: StubServer,
) -> None:
    status, content_type, body = _request(stub_server, "POST", "/v1/responses", TOKEN)

    assert (status, content_type) == (200, "text/event-stream")
    assert _sse_events(body)[1]["item"]["content"][0]["text"] == stub.REPLY_TEXT
    last = _log_entries(stub_server)[-1]
    assert last["authorized"] is True
    assert last["model"] == "gpt-6-luna"


@pytest.mark.parametrize("token", [None, "wrong-token"])
def test_stub_rejects_a_missing_or_wrong_token(
    stub_server: StubServer, token: str | None
) -> None:
    status, _, _ = _request(stub_server, "POST", "/v1/responses", token)

    assert status == 401
    assert _log_entries(stub_server)[-1]["authorized"] is False


def test_stub_answers_404_to_other_paths(stub_server: StubServer) -> None:
    assert _request(stub_server, "GET", "/v1/models?client_version=0", TOKEN)[0] == 404
    assert _request(stub_server, "POST", "/v1/chat/completions", TOKEN)[0] == 404


def test_stub_log_holds_no_token_or_request_content(stub_server: StubServer) -> None:
    _request(stub_server, "POST", "/v1/responses", TOKEN)

    log_text = stub_server.log.read_text()
    assert TOKEN not in log_text
    assert "secret prompt" not in log_text


def _write_log(path: Path, *entries: dict[str, object]) -> Path:
    path.write_text("".join(json.dumps(entry) + "\n" for entry in entries))
    return path


def _turn(model: str = "gpt-6-luna", *, authorized: bool = True) -> dict[str, object]:
    return {
        "method": "POST",
        "path": "/v1/responses",
        "authorized": authorized,
        "model": model,
    }


def test_judge_pass_needs_a_clean_smoke_and_an_authorized_turn(tmp_path: Path) -> None:
    log = _write_log(tmp_path / "log", _turn())

    assert run_smoke._judge("pass", 0, "", log) == []
    assert run_smoke._judge("pass", 1, "", log) == ["smoke.sh exited 1"]
    empty = _write_log(tmp_path / "empty")
    assert run_smoke._judge("pass", 0, "", empty) == [
        "no authorized Codex request reached the stub"
    ]
    unauthorized = _write_log(tmp_path / "unauthorized", _turn(authorized=False))
    assert run_smoke._judge("pass", 0, "", unauthorized) == [
        "no authorized Codex request reached the stub"
    ]


def test_judge_pass_rejects_a_turn_on_another_model(tmp_path: Path) -> None:
    log = _write_log(tmp_path / "log", _turn(), _turn("gpt-other"))

    assert run_smoke._judge("pass", 0, "", log) == [
        "a Codex request did not use the pinned model gpt-6-luna"
    ]


def test_judge_fail_needs_the_gateway_env_failure_and_no_turn(tmp_path: Path) -> None:
    empty = _write_log(tmp_path / "empty")
    output = (
        "SMOKE-FAIL gateway-env: missing BOOLEY_GATEWAY_URL\n"
        "SMOKE-FAIL doctor-gateway: no gateway credential PASS line\n"
    )

    assert run_smoke._judge("fail", 1, output, empty) == []
    assert run_smoke._judge("fail", 0, output, empty) == [
        "smoke.sh passed without the gateway environment"
    ]
    assert run_smoke._judge("fail", 1, "SMOKE-FAIL doctor: x\n", empty) == [
        "smoke.sh did not fail on its gateway-env check",
        "smoke.sh did not fail on its doctor-gateway check",
    ]
    log = _write_log(tmp_path / "log", _turn())
    assert run_smoke._judge("fail", 1, output, log) == [
        "1 Codex request(s) reached the stub"
    ]


def test_config_copy_drops_only_the_gateway_env(tmp_path: Path) -> None:
    original = json.loads(run_smoke.CONFIG.read_text())

    full = json.loads(
        run_smoke._write_config(
            tmp_path, without_gateway_env=False, image=None
        ).read_text()
    )
    stripped = json.loads(
        run_smoke._write_config(
            tmp_path, without_gateway_env=True, image="example/img"
        ).read_text()
    )

    assert full == original
    assert set(original["containerEnv"]) - set(stripped["containerEnv"]) == set(
        run_smoke.GATEWAY_ENV
    )
    assert stripped["image"] == "example/img"


def test_config_points_the_gateway_at_the_stub() -> None:
    env = json.loads(run_smoke.CONFIG.read_text())["containerEnv"]

    assert env["BOOLEY_PRIMARY_AUTH"] == "gateway"
    assert env["BOOLEY_GATEWAY_URL"] == (
        f"https://{run_smoke.STUB_HOST}:{run_smoke.STUB_PORT}/v1"
    )
    assert (
        env["CODEX_CA_CERTIFICATE"]
        == f"{run_smoke.CONTAINER_STUB_DIR}/certs/{stub.CA_CERT}"
    )


@pytest.fixture
def sibling_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the smoke at a fake checkout inside *tmp_path*; return its parent."""
    monkeypatch.setattr(run_smoke, "REPO_ROOT", tmp_path / "demo")
    return tmp_path


def test_fresh_sibling_dirs_refuses_a_directory_it_did_not_create(
    sibling_root: Path,
) -> None:
    (sibling_root / "picorv32").mkdir()
    (sibling_root / "picorv32" / "keep.v").write_text("module keep; endmodule\n")

    with pytest.raises(SystemExit, match="not created by this smoke"):
        run_smoke._fresh_sibling_dirs()
    assert (sibling_root / "picorv32" / "keep.v").exists()


def test_fresh_sibling_dirs_replaces_an_earlier_smokes_directories(
    sibling_root: Path,
) -> None:
    first = run_smoke._fresh_sibling_dirs()
    (first / "token").write_text("old\n")
    (sibling_root / "picorv32").mkdir()

    second = run_smoke._fresh_sibling_dirs()

    assert second == sibling_root / "gateway-stub"
    assert not (second / "token").exists()
    assert not (sibling_root / "picorv32").exists()
    assert (second / run_smoke.OWNER_MARKER).is_file()
