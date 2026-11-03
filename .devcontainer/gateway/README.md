# Sponsored demo gateway client

With no Claude or Codex credential of the visitor's own, Booley's
`BOOLEY_AGENT_APP=auto` runs Codex through the Booley demo gateway
(`BOOLEY_GATEWAY_*` in `../devcontainer.json`). The gateway holds the OpenAI
key; the Codespace only gets a revocable per-visitor token.

- `claim.sh` and `token.sh` are copied unchanged from the gateway project's
  `client/` directory at commit `d768546b429cff51d77ae5f17795595f3b4ce6b5`.
  Update them by copying that directory again and changing this line.
  `claim.sh` carries the notice and its `NOTICE_VERSION`; the gateway accepts
  only the versions it lists.
- `bin/booley-demo-claim` runs `claim.sh` against the gateway root (Booley's
  URL ends in `/v1`).
- `shell-path.sh` is sourced from `~/.bashrc` and puts `booley-demo-claim`
  on an interactive shell's `PATH`. The visitor runs it (`START-HERE.md`
  step 1); nothing offers it automatically, because the Dashboard terminal
  opens over the first terminal when the visitor clicks Trust.
