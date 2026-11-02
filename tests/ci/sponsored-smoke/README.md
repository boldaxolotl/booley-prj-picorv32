# Sponsored-mode CI smoke

The `Sponsored-mode smoke` workflow boots the sponsored (gateway) Codespaces
environment headless and checks that it works without any real credential:

- `gateway_stub.py` stands in for the demo gateway. It serves TLS with a
  throwaway CA and answers Codex's `POST /v1/responses` with a canned reply,
  but only for the bearer token generated for that run.
- `run_smoke.py` derives the environment under test from the demo's real
  `.devcontainer/devcontainer.json` (`sponsored_config`); there is no fixture
  copy to drift. It starts from the Codespaces smoke's headless derivation
  (`ci_config` in `../codespaces-smoke/run_smoke.py`: the checkout's parent
  mounted at `/workspaces` as in a Codespace, no extensions, host requirements
  or `postAttachCommand`, CPU and memory capped to the smallest Codespace).
  On top of that it changes only what pointing the shipped sponsored mode at
  the stub needs, in both `containerEnv` and `remoteEnv`:
  - `BOOLEY_GATEWAY_URL` → `https://gateway-stub:8443/v1`, the stub;
  - `BOOLEY_DEMO_TOKEN_FILE` → `/workspaces/gateway-stub/token`, so the
    shipped `.devcontainer/gateway/token.sh` prints the run's throwaway token
    (shaped `bgw_…` as that script requires) instead of a claimed one;
  - `CODEX_CA_CERTIFICATE` → the stub's throwaway CA, which Codex must trust;
  - `runArgs` gains `--add-host=gateway-stub:host-gateway`.

  Everything else is the shipped spec: the image, users, `BOOLEY_AGENT_APP`
  and `BOOLEY_PRIMARY_AUTH` (both `auto`), the token command, the model, and
  every lifecycle command, including the real `on-create.sh` (upstream clone,
  firmware build and PDK fetch, as visitors get). The derivation refuses a spec
  that does not ship the `BOOLEY_GATEWAY_*` settings.
- `smoke.sh` runs inside the container. It checks the gateway environment,
  that `BOOLEY_AGENT_APP=auto` chose Codex through the gateway, the absence of
  agent credentials, `booley doctor` (no FAIL, the gateway credential PASS, no
  `agent.*` WARN) and one `codex exec` answered by the stub.
- `run_smoke.py` drives one run: stub, `devcontainer up`, `smoke.sh`, the stub's
  request log, teardown. `--without-gateway-env` is the negative run: it removes
  the three `BOOLEY_GATEWAY_*` variables (leaving `auto` as shipped), so the
  smoke must fail on its `gateway-env` and `doctor-gateway` checks and no
  request may reach the stub.

`tests/ci/test_sponsored_smoke.py` pins the derivation: the derived config
equals the real spec plus exactly these overrides.

## Run it locally

Needs Linux, Docker and Node. The config mounts the checkout's parent
directory, and the run creates `../gateway-stub` and `../picorv32`, so use a
clone in an otherwise empty directory. Don't run it at the same time as the
Codespaces smoke from the same parent directory: both use `../picorv32`.

```bash
mkdir -p ~/scratch/smoke && git clone <this repo> ~/scratch/smoke/booley-prj-picorv32
cd ~/scratch/smoke/booley-prj-picorv32
python3 tests/ci/sponsored-smoke/run_smoke.py --expect pass
python3 tests/ci/sponsored-smoke/run_smoke.py --expect fail --without-gateway-env
```

`--image` boots another image, for example to try a repin; `--keep` leaves the
container running for inspection.
