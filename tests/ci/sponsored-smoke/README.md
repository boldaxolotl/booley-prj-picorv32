# Sponsored-mode CI smoke

The `Sponsored-mode smoke` workflow boots the sponsored (gateway) Codespaces
environment headless and checks that it works without any real credential:

- `gateway_stub.py` stands in for the demo gateway. It serves TLS with a
  throwaway CA and answers Codex's `POST /v1/responses` with a canned reply,
  but only for the bearer token generated for that run.
- `devcontainer.json` is the environment under test. It mirrors the demo's
  Codespaces layout (upstream PicoRV32 at `/workspaces/picorv32`, its `.booley`
  linked to this repo) and points `BOOLEY_GATEWAY_URL` at the stub. It drops
  what only the browser needs (VS Code extensions, sshd, `postAttachCommand`)
  and adds what only CI needs: the checkout's parent mounted at `/workspaces`
  as in a Codespace, the `gateway-stub` host alias, and `CODEX_CA_CERTIFICATE`
  so Codex trusts the stub.
- `smoke.sh` runs inside the container. It checks the gateway environment, the
  absence of agent credentials, `booley doctor` (no FAIL, the gateway
  credential PASS, no `agent.*` WARN) and one `codex exec` answered by the stub.
- `run_smoke.py` drives one run: stub, `devcontainer up`, `smoke.sh`, the stub's
  request log, teardown. `--without-gateway-env` is the negative run: the smoke
  must fail on its `gateway-env` check and no request may reach the stub.

When the demo ships its own `.devcontainer/devcontainer.json`, keep this
fixture in step with it (image, environment, lifecycle commands).

## Run it locally

Needs Linux, Docker and Node. The config mounts the checkout's parent
directory, and the run creates `../gateway-stub` and `../picorv32`, so use a
clone in an otherwise empty directory:

```bash
mkdir -p ~/scratch/smoke && git clone <this repo> ~/scratch/smoke/booley-prj-picorv32
cd ~/scratch/smoke/booley-prj-picorv32
python3 tests/ci/sponsored-smoke/run_smoke.py --expect pass
python3 tests/ci/sponsored-smoke/run_smoke.py --expect fail --without-gateway-env
```

`--image` boots another image, for example to try a repin; `--keep` leaves the
container running for inspection.
