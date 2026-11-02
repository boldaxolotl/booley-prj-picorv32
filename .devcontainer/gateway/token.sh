#!/usr/bin/env bash
#
# Print the Booley demo gateway token, for Codex's `auth.command` and for
# Booley's child processes. Exits 1 with a hint on stderr when there is no
# token yet (claim.sh writes it).
set -euo pipefail

TOKEN_FILE="${BOOLEY_DEMO_TOKEN_FILE:-$HOME/.config/booley-demo/token}"

token=""
if [[ -r $TOKEN_FILE ]]; then
  IFS= read -r token <"$TOKEN_FILE" || true
fi
if [[ ! $token =~ ^bgw_[A-Za-z0-9_-]{20,}$ ]]; then
  echo "token.sh: no Booley demo token yet; run claim.sh first" >&2
  exit 1
fi
printf '%s\n' "$token"
