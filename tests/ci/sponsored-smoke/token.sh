#!/usr/bin/env bash
# Gateway token command for the sponsored-mode CI smoke (BOOLEY_GATEWAY_TOKEN_COMMAND).
# Same contract as the demo's real token script: print the claimed token on
# stdout, or exit 1 with an instruction on stderr. The CI workflow "claims" a
# throwaway token by writing it next to the stub's certificates.
set -euo pipefail
token_file=/workspaces/gateway-stub/token
if [[ ! -s "$token_file" ]]; then
    echo "no gateway token at $token_file: start the gateway stub first" >&2
    exit 1
fi
tr -d '\n' < "$token_file"
