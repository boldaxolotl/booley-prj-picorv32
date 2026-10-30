#!/usr/bin/env python3
"""Boot the demo's Codespaces config headless and run the first-five-minutes checks.

One run of the Codespaces CI smoke, the same in CI and on a developer machine
(Linux with Docker and Node):

1. Derive a CI config from the real ``.devcontainer/devcontainer.json``
   (:func:`ci_config`) and write it to ``../codespaces-smoke``.
2. ``devcontainer up`` that config. Its own ``initializeCommand`` and
   ``onCreateCommand`` build the Codespaces layout: ``../picorv32`` is the
   upstream checkout and its ``.booley`` links to this repository.
3. Run ``smoke.sh`` in the container: layout, agent choice, Git identity,
   Doctor, and the lint, simulation and synthesis Targets.
4. Remove the container.

Exit 0 when every check passed. No credential is used: the container starts
with none, which is also what a visitor without Codespaces secrets gets.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
SPEC = REPO_ROOT / ".devcontainer" / "devcontainer.json"
DEVCONTAINER_CLI = "@devcontainers/cli@0.90.0"
# Codespaces mounts the VM's /workspaces, which holds this repository's clone.
# The devcontainer CLI mounts only the repository, so mount its parent instead.
WORKSPACE_MOUNT = "source=${localWorkspaceFolder}/..,target=/workspaces,type=bind"
# Parts of the spec only a Codespace or an attached editor uses. The CLI either
# ignores them or, for postAttachCommand, would run editor setup with no editor.
EDITOR_ONLY_KEYS = ("customizations", "postAttachCommand", "secrets", "hostRequirements")
# The smallest Codespace the spec's hostRequirements allow. CI runners are
# larger, so cap the container to catch a demo that no longer fits.
CODESPACE_LIMITS = ["--cpus=2", "--memory=8g"]
# Agent credentials a Codespace may receive as secrets. The smoke clears them,
# so a developer's own environment cannot change the agent choice under test.
CREDENTIAL_ENV = ("ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN", "OPENAI_API_KEY")
# Upper bounds for each external step. `up` pulls a multi-GB image, clones
# upstream and fetches the PDK; `exec` runs Doctor, lint, simulation and synthesis.
UP_TIMEOUT_S = 40 * 60
EXEC_TIMEOUT_S = 30 * 60
DOCKER_TIMEOUT_S = 120
# Marks ../codespaces-smoke (and so ../picorv32) as created by this script.
OWNER_MARKER = ".codespaces-smoke"
CONTAINER_SMOKE_DIR = "/workspaces/codespaces-smoke"
# Ignored directories where a booted Booley keeps state in this checkout.
STATE_DIRS = ("runtime", ".runtime")


def _log(message: str) -> None:
    print(f"[codespaces-smoke] {message}", flush=True)


def ci_config(spec: dict[str, object], *, image: str | None = None) -> dict[str, object]:
    """Return the config CI boots: *spec* with the Codespaces mount and no editor-only parts.

    Everything that shapes the running environment (image, users, environment,
    workspace folder and lifecycle commands) is kept unchanged, so the smoke
    tests the spec visitors get.
    """
    config = copy.deepcopy(spec)
    for key in EDITOR_ONLY_KEYS:
        config.pop(key, None)
    config["workspaceMount"] = WORKSPACE_MOUNT
    run_args = config.get("runArgs", [])
    assert isinstance(run_args, list)
    config["runArgs"] = [*run_args, *CODESPACE_LIMITS]
    if image:
        config["image"] = image
    return config


def _devcontainer(
    *args: str, timeout: int, capture: bool = False, check: bool = True
) -> subprocess.CompletedProcess[str]:
    """Run the pinned devcontainer CLI; stream its output unless *capture* is set.

    With *check*, a nonzero exit raises.
    """
    _log("$ devcontainer " + " ".join(args))
    environment = {
        name: value for name, value in os.environ.items() if name not in CREDENTIAL_ENV
    }
    return subprocess.run(
        ["npx", "--yes", DEVCONTAINER_CLI, *args],
        check=check,
        capture_output=capture,
        text=True,
        timeout=timeout,
        env=environment,
    )


def _fresh_sibling_dirs() -> Path:
    """Remove the previous run's sibling directories and return a new smoke directory.

    The smoke owns ``../codespaces-smoke`` and ``../picorv32`` (the upstream
    checkout on-create clones). A marker file proves an earlier smoke created
    them; without it, refuse rather than touch a directory someone else owns,
    such as a real PicoRV32 clone beside this repo.
    """
    # An earlier boot leaves ignored Booley state in this checkout. Against a
    # freshly cloned ../picorv32 it reads as a visitor's choices (for example a
    # removed Dashboard task), so the run would not test a first start.
    stale = [name for name in STATE_DIRS if (REPO_ROOT / name).exists()]
    if stale:
        raise SystemExit(
            f"{REPO_ROOT} holds Booley state from an earlier boot ({', '.join(stale)});"
            " run from a fresh clone"
        )
    parent = REPO_ROOT.parent
    smoke_dir, upstream = parent / "codespaces-smoke", parent / "picorv32"
    ours = (smoke_dir / OWNER_MARKER).is_file()
    for path in (smoke_dir, upstream):
        if path.exists() and not ours:
            raise SystemExit(
                f"{path} exists and was not created by this smoke; run from a"
                " checkout in an otherwise empty directory"
            )
    for path in (smoke_dir, upstream):
        if path.exists():
            shutil.rmtree(path)
    smoke_dir.mkdir()
    (smoke_dir / OWNER_MARKER).write_text("created by run_smoke.py\n", encoding="utf-8")
    return smoke_dir


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


def run(*, image: str | None, keep: bool) -> int:
    """Run one smoke and return 0 when every check passed."""
    smoke_dir = _fresh_sibling_dirs()
    evidence = smoke_dir / "evidence"
    evidence.mkdir()
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    config = smoke_dir / "devcontainer.json"
    config.write_text(json.dumps(ci_config(spec, image=image), indent=2) + "\n", encoding="utf-8")
    label = f"booley.codespaces-smoke={secrets.token_hex(4)}"
    common = ("--workspace-folder", str(REPO_ROOT), "--config", str(config), "--id-label", label)
    try:
        _devcontainer("up", *common, "--remove-existing-container", timeout=UP_TIMEOUT_S)
        # Output streams live; smoke.sh also keeps each check's log in the
        # mounted evidence directory, so a timeout still leaves evidence.
        result = _devcontainer(
            "exec", *common, "bash",
            f"/workspaces/{REPO_ROOT.name}/tests/ci/codespaces-smoke/smoke.sh",
            f"{CONTAINER_SMOKE_DIR}/evidence",
            capture=False,
            check=False,
            timeout=EXEC_TIMEOUT_S,
        )  # fmt: skip
    finally:
        if not keep:
            subprocess.run(
                ["docker", "rm", "-f", *_containers(label)],
                check=False,
                capture_output=True,
                timeout=DOCKER_TIMEOUT_S,
            )
    if result.returncode != 0:
        _log(f"smoke.sh exited {result.returncode}; evidence in {evidence}")
        return 1
    _log("all checks passed")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--image", help="boot this image instead of the pinned one")
    parser.add_argument("--keep", action="store_true", help="leave the container running")
    args = parser.parse_args(argv)
    if os.name != "posix":
        raise SystemExit("the Codespaces smoke needs Linux with Docker")
    return run(image=args.image, keep=args.keep)


if __name__ == "__main__":
    sys.exit(main())
