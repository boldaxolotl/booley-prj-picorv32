"""Static checks on the demo's Codespaces config and the CI config derived from it."""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = REPO_ROOT / ".devcontainer" / "devcontainer.json"
ON_CREATE = REPO_ROOT / ".devcontainer" / "on-create.sh"
SMOKE_DIR = Path(__file__).parent / "codespaces-smoke"


def _load_run_smoke() -> ModuleType:
    """Import run_smoke.py from its hyphenated directory."""
    spec = importlib.util.spec_from_file_location("run_smoke", SMOKE_DIR / "run_smoke.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


run_smoke = _load_run_smoke()


def _spec() -> dict[str, object]:
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def test_repository_has_exactly_one_devcontainer_config() -> None:
    # With more than one devcontainer.json, Codespaces ignores workspaceFolder
    # and opens this repository instead of the PicoRV32 Project (#2257).
    # These are the locations Codespaces discovers configs in; CI fixtures
    # elsewhere (tests/ci/) are invisible to it.
    patterns = (".devcontainer.json", ".devcontainer/devcontainer.json", ".devcontainer/*/devcontainer.json")
    configs = sorted(
        path.relative_to(REPO_ROOT).as_posix() for pattern in patterns for path in REPO_ROOT.glob(pattern)
    )
    assert configs == [".devcontainer/devcontainer.json"]


def test_image_is_pinned_to_a_release_or_candidate_tag() -> None:
    image = str(_spec()["image"])
    repository, _, tag = image.rpartition(":")
    assert repository == "ghcr.io/boldaxolotl/booley-sandbox-riscv"
    assert re.fullmatch(r"\d+\.\d+\.\d+|candidate-[0-9a-f]{40}-\d+-\d+", tag), tag


def test_container_and_remote_environments_match() -> None:
    # Lifecycle commands see containerEnv; terminals and the editor see
    # remoteEnv. Booley must find the same settings in both.
    spec = _spec()
    assert spec["containerEnv"] == spec["remoteEnv"]


def test_environment_selects_auto_agent_and_neutral_git_identity() -> None:
    env = _spec()["containerEnv"]
    assert isinstance(env, dict)
    assert env["BOOLEY_AGENT_APP"] == "auto"
    assert env["BOOLEY_PRIMARY_AUTH"] == "auto"
    # The complete command-scope identity Doctor's override check asks for.
    assert {key: env[key] for key in env if key.startswith("GIT_CONFIG_")} == {
        "GIT_CONFIG_COUNT": "2",
        "GIT_CONFIG_KEY_0": "user.name",
        "GIT_CONFIG_VALUE_0": "Dev",
        "GIT_CONFIG_KEY_1": "user.email",
        "GIT_CONFIG_VALUE_1": "dev@localhost",
    }


def test_project_paths_agree_between_spec_and_on_create() -> None:
    spec = _spec()
    env = spec["containerEnv"]
    assert isinstance(env, dict)
    project = str(spec["workspaceFolder"])
    assert f"PROJECT={project}\n" in ON_CREATE.read_text(encoding="utf-8")
    assert env["BOOLEY_DIR"] == f"{project}/.booley"
    # initializeCommand must create the folder lifecycle commands start in.
    assert f"/../{Path(project).name}" in str(spec["initializeCommand"])


def test_secrets_offer_every_credential_auto_understands() -> None:
    secrets = _spec()["secrets"]
    assert isinstance(secrets, dict)
    assert set(secrets) == set(run_smoke.CREDENTIAL_ENV)


def test_ci_config_keeps_the_environment_and_drops_editor_parts() -> None:
    spec = _spec()
    config = run_smoke.ci_config(spec)

    for key in run_smoke.EDITOR_ONLY_KEYS:
        assert key not in config
    assert config["workspaceMount"] == run_smoke.WORKSPACE_MOUNT
    for key in (
        "image",
        "remoteUser",
        "containerUser",
        "workspaceFolder",
        "containerEnv",
        "remoteEnv",
        "initializeCommand",
        "onCreateCommand",
        "postCreateCommand",
        "postStartCommand",
    ):
        assert config[key] == spec[key], key
    assert config["runArgs"][-len(run_smoke.CODESPACE_LIMITS) :] == run_smoke.CODESPACE_LIMITS
    # The spec itself is left untouched.
    assert spec == _spec()


def test_ci_config_can_swap_the_image() -> None:
    config = run_smoke.ci_config(_spec(), image="example/image:tag")
    assert config["image"] == "example/image:tag"


def test_open_files_resolve_from_the_workspace_folder() -> None:
    # Codespaces resolves openFiles from workspaceFolder (/workspaces/picorv32),
    # not from this repository's root, so files here are reached through the
    # Project's .booley link.
    open_files = _spec()["customizations"]["codespaces"]["openFiles"]
    assert open_files
    for entry in open_files:
        assert entry.startswith(".booley/"), entry
        assert (REPO_ROOT / entry.removeprefix(".booley/")).is_file(), entry
