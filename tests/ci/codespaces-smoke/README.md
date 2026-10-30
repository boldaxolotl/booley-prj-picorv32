# Codespaces CI smoke

The `Codespaces smoke` workflow boots the demo's real
`.devcontainer/devcontainer.json` headless and checks what a visitor's first
five minutes depend on:

- `run_smoke.py` derives the CI config from the real spec (`ci_config`). It
  keeps the image, users, environment, workspace folder and lifecycle
  commands, and drops what only a Codespace or an attached editor uses
  (extensions, secrets prompts, host requirements, `postAttachCommand`). It
  mounts the checkout's parent at `/workspaces`, as Codespaces does, then runs
  `devcontainer up`, `smoke.sh`, and teardown.
- `smoke.sh` runs inside the container: the `/workspaces/picorv32` layout, the
  `BOOLEY_AGENT_APP=auto` choice with no credential (Claude Code with sign-in
  offered), the agent Git identity, `booley doctor`, `booley targets`, and the
  `lint_core`, `sim_core` and `synth_core` Targets.

No credential is used. The run clears agent credential variables from its own
environment before booting.

`tests/ci/test_codespaces_spec.py` checks the spec statically, including that
the repository has exactly one devcontainer config: with more than one,
Codespaces ignores `workspaceFolder` and opens this repository instead of the
PicoRV32 Project.

## Run it locally

Needs Linux, Docker and Node. The config mounts the checkout's parent
directory, and the run creates `../codespaces-smoke` and `../picorv32`, so use
a fresh clone in an otherwise empty directory for each run (a booted
checkout keeps Booley state that the next run refuses). Don't run it at the same time as the
sponsored smoke from the same parent directory: both use `../picorv32`.

```bash
mkdir -p ~/scratch/cs-smoke && git clone <this repo> ~/scratch/cs-smoke/booley-prj-picorv32
cd ~/scratch/cs-smoke/booley-prj-picorv32
python3 tests/ci/codespaces-smoke/run_smoke.py
```

`--image` boots another image, for example to try a repin; `--keep` leaves the
container running for inspection.

## What it cannot check

Which folder the Codespaces browser and desktop clients open, whether
`CODESPACES.md` and the Dashboard open on first start, and the agent sign-in
itself all need a real Codespace and a person at the client.
