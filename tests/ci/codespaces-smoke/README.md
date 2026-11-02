# Codespaces CI smoke

The `Codespaces smoke` workflow boots the demo's real
`.devcontainer/devcontainer.json` headless and checks what a visitor's first
five minutes depend on:

- `run_smoke.py` derives the CI config from the real spec (`ci_config`). It
  keeps the image, users, environment, workspace folder and lifecycle
  commands, and drops what only a Codespace or an attached editor uses
  (extensions, host requirements, `postAttachCommand`). It
  mounts the checkout's parent at `/workspaces`, as Codespaces does, then runs
  `devcontainer up`, `smoke.sh`, and teardown.
- `smoke.sh` runs inside the container: the `/workspaces/picorv32` layout;
  the `BOOLEY_AGENT_APP=auto` choice with no credential (Codex through the
  demo gateway, recorded as `codex|gateway`, before any demo token exists);
  the first-terminal sign-in hook (`booley-demo-claim` on an interactive
  shell's `PATH`, no offer used up without a terminal); Claude Code's
  first-run prompts marked done; the agent Git identity; `booley doctor` before the
  demo sign-in (its only allowed FAIL is the missing demo token, see below)
  and with a stand-in demo token (no FAIL, the gateway credential passes),
  each with no warning but the expected ones; `booley targets`; and the
  `lint_core`, `sim_core` and `synth_core` Targets. It runs
  `tests/ci/test_goalsets.py` with the image's Booley: every Goalset parses,
  and Goal Mode entry accepts the `zbb` Goals in the checkout. Last, it checks
  the own-account switch: after a stand-in Codex login and a registrar re-run,
  the choice is `codex|auto` and `booley chat` starts Codex; with a stand-in
  Claude login as well it is `claude|auto` and `booley chat` starts Claude
  Code; with both removed it falls back to `codex|gateway`.

No credential is used, and no request reaches the real gateway: the run
clears agent credential variables from its own environment before booting,
and the stand-in logins only drive the choice and `booley chat -- --version`.
Requests through the gateway are the sponsored smoke's job
(`../sponsored-smoke`).

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

## Doctor before the demo sign-in

With no demo token yet, Doctor runs `BOOLEY_GATEWAY_TOKEN_COMMAND`, which
exits 1, and grades the gateway credential (`agent.credential-missing`). The
pinned Booley FAILs it; newer Booley warns instead when `BOOLEY_AGENT_APP=auto`
picked the gateway. `CODESPACES.md` tells visitors the check fails until they
have a token. The smoke accepts that one finding, as a FAIL or a warning,
requires Doctor to finish, and fails on anything else.

## What it cannot check

Which folder the Codespaces browser and desktop clients open, whether
`CODESPACES.md` and the Dashboard open on first start, and the agent sign-in
itself all need a real Codespace and a person at the client.
