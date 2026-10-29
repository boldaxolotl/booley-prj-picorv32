#!/usr/bin/env python3
"""Boot the sponsored-mode devcontainer headless against the gateway stub.

One run of the sponsored-mode CI smoke, the same in CI and on a developer
machine (Linux with Docker and Node):

1. Create a throwaway TLS CA and token beside the repo checkout, in
   ``../gateway-stub`` (the config mounts the checkout's parent at
   ``/workspaces``, as Codespaces does), and start ``gateway_stub.py``.
2. ``devcontainer up`` a copy of the fixture config. ``--without-gateway-env``
   removes the gateway variables (the negative run); ``--image`` swaps the
   pinned image, for example to try a repin.
3. Run ``smoke.sh`` in the container, then check the stub's request log.
4. Remove the container and stop the stub.

``--expect pass``: every smoke check passes and the stub answered at least
one authorized Codex request for the pinned model.
``--expect fail``: the smoke fails on its ``gateway-env`` check and no Codex
request reached the stub.

Exit 0 when the run matched the expectation. No real credential is used: the
token is random, and the container gets no agent credential.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from gateway_stub import RESPONSES_SUFFIX  # sibling script, found via sys.path

REPO_ROOT = HERE.parents[2]
CONFIG = HERE / "devcontainer.json"
STUB = HERE / "gateway_stub.py"
# The stub's name inside the container (runArgs adds it as a host alias) and
# its port; both must match BOOLEY_GATEWAY_URL in the config.
STUB_HOST = "gateway-stub"
STUB_PORT = 8443
DEVCONTAINER_CLI = "@devcontainers/cli@0.90.0"
# Removed from containerEnv for the negative run.
GATEWAY_ENV = (
    "BOOLEY_PRIMARY_AUTH",
    "BOOLEY_GATEWAY_URL",
    "BOOLEY_GATEWAY_TOKEN_COMMAND",
    "BOOLEY_GATEWAY_MODEL",
)
# Upper bounds for each external step. `up` pulls a multi-GB image, clones
# upstream and fetches the PDK; `exec` runs Doctor and one Codex turn.
UP_TIMEOUT_S = 40 * 60
EXEC_TIMEOUT_S = 20 * 60
DOCKER_TIMEOUT_S = 120
# Marks ../gateway-stub (and so ../picorv32) as created by this script.
OWNER_MARKER = ".sponsored-smoke"
# Where the container sees the stub directory; smoke.sh writes evidence there.
CONTAINER_STUB_DIR = "/workspaces/gateway-stub"


def _log(message: str) -> None:
    print(f"[sponsored-smoke] {message}", flush=True)


def _devcontainer(
    *args: str, timeout: int, capture: bool = False
) -> subprocess.CompletedProcess[str]:
    """Run the pinned devcontainer CLI; without *capture*, stream output and fail on error."""
    _log("$ devcontainer " + " ".join(args))
    return subprocess.run(
        ["npx", "--yes", DEVCONTAINER_CLI, *args],
        check=not capture,
        capture_output=capture,
        text=True,
        timeout=timeout,
    )


def _fresh_sibling_dirs() -> Path:
    """Remove the previous run's sibling directories and return a new stub directory.

    The smoke owns ``../gateway-stub`` and ``../picorv32`` (the upstream
    checkout on-create clones). A marker file proves an earlier smoke created
    them; without it, refuse rather than touch a directory someone else owns,
    such as a real PicoRV32 clone beside this repo.
    """
    parent = REPO_ROOT.parent
    stub_dir, upstream = parent / "gateway-stub", parent / "picorv32"
    ours = (stub_dir / OWNER_MARKER).is_file()
    for path in (stub_dir, upstream):
        if path.exists() and not ours:
            raise SystemExit(
                f"{path} exists and was not created by this smoke; run from a"
                " checkout in an otherwise empty directory"
            )
    for path in (stub_dir, upstream):
        shutil.rmtree(path, ignore_errors=True)
    stub_dir.mkdir()
    (stub_dir / OWNER_MARKER).write_text("created by run_smoke.py\n", encoding="utf-8")
    return stub_dir


def _write_config(
    stub_dir: Path, *, without_gateway_env: bool, image: str | None
) -> Path:
    """Write the config to boot: the fixture, optionally without the gateway variables."""
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    if without_gateway_env:
        for name in GATEWAY_ENV:
            config["containerEnv"].pop(name)
    if image:
        config["image"] = image
    derived = stub_dir / "devcontainer.json"
    derived.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return derived


def _start_stub(stub_dir: Path) -> tuple[subprocess.Popen[bytes], Path]:
    """Create certificates and a token, start the stub, and wait until it listens."""
    certs = stub_dir / "certs"
    subprocess.run(
        [
            sys.executable,
            str(STUB),
            "make-certs",
            "--dir",
            str(certs),
            "--host",
            STUB_HOST,
        ],
        check=True,
        timeout=120,
    )
    token_file = stub_dir / "token"
    token_file.write_text(f"stub-{secrets.token_hex(16)}\n", encoding="utf-8")
    request_log = stub_dir / "requests.jsonl"
    stub = subprocess.Popen(
        [
            sys.executable, str(STUB), "serve", "--dir", str(certs),
            "--port", str(STUB_PORT), "--token-file", str(token_file),
            "--log", str(request_log),
        ],
    )  # fmt: skip
    for _ in range(50):
        if request_log.exists():
            return stub, request_log
        if stub.poll() is not None:
            raise SystemExit(f"gateway stub exited with {stub.returncode}")
        time.sleep(0.1)
    stub.kill()
    raise SystemExit("gateway stub did not start")


def _responses_requests(request_log: Path) -> list[dict[str, object]]:
    """Return the logged Codex turn requests (POST .../responses)."""
    entries = [
        json.loads(line)
        for line in request_log.read_text(encoding="utf-8").splitlines()
    ]
    return [
        entry
        for entry in entries
        if entry["method"] == "POST"
        and str(entry["path"]).rstrip("/").endswith(RESPONSES_SUFFIX)
    ]


def _judge(
    expect: str, smoke_status: int, smoke_output: str, request_log: Path
) -> list[str]:
    """Return why this run does not match *expect* (empty when it matches)."""
    requests = _responses_requests(request_log)
    problems = []
    if expect == "pass":
        if smoke_status != 0:
            problems.append(f"smoke.sh exited {smoke_status}")
        authorized = [entry for entry in requests if entry["authorized"]]
        if not authorized:
            problems.append("no authorized Codex request reached the stub")
        model = json.loads(CONFIG.read_text(encoding="utf-8"))["containerEnv"][
            "BOOLEY_GATEWAY_MODEL"
        ]
        if any(entry["model"] != model for entry in authorized):
            problems.append(f"a Codex request did not use the pinned model {model}")
    else:
        if smoke_status == 0:
            problems.append("smoke.sh passed without the gateway environment")
        # Both the smoke's own check and Doctor must notice the missing gateway.
        for check in ("gateway-env", "doctor-gateway"):
            if f"SMOKE-FAIL {check}" not in smoke_output:
                problems.append(f"smoke.sh did not fail on its {check} check")
        if requests:
            problems.append(f"{len(requests)} Codex request(s) reached the stub")
    return problems


def _teardown(label: str, stub: subprocess.Popen[bytes], *, keep: bool) -> None:
    """Remove the container, then stop the stub."""
    # Remove the container first: it must not leak even if the stub hangs.
    if not keep:
        subprocess.run(
            ["docker", "rm", "-f", *_containers(label)],
            check=False,
            capture_output=True,
            timeout=DOCKER_TIMEOUT_S,
        )
    stub.terminate()
    try:
        stub.wait(timeout=10)
    except subprocess.TimeoutExpired:
        stub.kill()
        stub.wait()


def run(
    expect: str, *, without_gateway_env: bool, image: str | None, keep: bool
) -> int:
    """Run one smoke and return 0 when its outcome matches *expect*."""
    stub_dir = _fresh_sibling_dirs()
    evidence = stub_dir / "evidence"
    evidence.mkdir()
    label = f"booley.sponsored-smoke={secrets.token_hex(4)}"
    config = _write_config(
        stub_dir, without_gateway_env=without_gateway_env, image=image
    )
    stub, request_log = _start_stub(stub_dir)
    try:
        _devcontainer(
            "up", "--workspace-folder", str(REPO_ROOT), "--config", str(config),
            "--id-label", label, "--remove-existing-container",
            timeout=UP_TIMEOUT_S,
        )  # fmt: skip
        result = _devcontainer(
            "exec", "--workspace-folder", str(REPO_ROOT), "--config", str(config),
            "--id-label", label, "bash",
            f"/workspaces/{REPO_ROOT.name}/tests/ci/sponsored-smoke/smoke.sh",
            f"{CONTAINER_STUB_DIR}/evidence",
            capture=True,
            timeout=EXEC_TIMEOUT_S,
        )  # fmt: skip
        print(result.stdout, end="")
        print(result.stderr, end="", file=sys.stderr)
        (evidence / "smoke.txt").write_text(result.stdout, encoding="utf-8")
        problems = _judge(expect, result.returncode, result.stdout, request_log)
    finally:
        _teardown(label, stub, keep=keep)
    _log(f"stub request log: {request_log}")
    for problem in problems:
        _log(f"UNEXPECTED: {problem}")
    if problems:
        return 1
    _log(f"outcome matched --expect {expect}")
    return 0


def _containers(label: str) -> list[str]:
    """Return the ids of containers carrying *label*."""
    listing = subprocess.run(
        ["docker", "ps", "-aq", "--filter", f"label={label}"],
        check=False,
        capture_output=True,
        text=True,
        timeout=DOCKER_TIMEOUT_S,
    )
    return listing.stdout.split()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--expect", choices=("pass", "fail"), required=True)
    parser.add_argument(
        "--without-gateway-env",
        action="store_true",
        help="boot without the gateway variables (the negative run)",
    )
    parser.add_argument("--image", help="boot this image instead of the pinned one")
    parser.add_argument(
        "--keep", action="store_true", help="leave the container running"
    )
    args = parser.parse_args(argv)
    if os.name != "posix":
        raise SystemExit("the sponsored smoke needs Linux with Docker")
    return run(
        args.expect,
        without_gateway_env=args.without_gateway_env,
        image=args.image,
        keep=args.keep,
    )


if __name__ == "__main__":
    sys.exit(main())
