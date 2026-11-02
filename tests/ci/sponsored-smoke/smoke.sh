#!/usr/bin/env bash
# Sponsored-mode smoke checks, run inside the booted devcontainer.
#
# Proves that the demo's shipped config works in sponsored mode with no real
# credential: the gateway environment is set, BOOLEY_AGENT_APP=auto chose
# Codex through the gateway, Doctor reports no FAIL and no agent credential
# WARN, and one interactive Codex request is answered by the gateway stub. Every check runs even after an earlier one fails, and each
# prints one "SMOKE-PASS <check>" or "SMOKE-FAIL <check>: <reason>" line, so
# the negative CI run can assert *why* the smoke failed. Exit 1 when any check
# failed.
#
# Usage: smoke.sh EVIDENCE_DIR
set -uo pipefail

evidence_dir=${1:?usage: smoke.sh EVIDENCE_DIR}
project_root=/workspaces/picorv32
# Must match REPLY_TEXT in gateway_stub.py.
stub_reply=BOOLEY-GATEWAY-STUB-OK
mkdir -p "$evidence_dir"
failures=0

pass() { echo "SMOKE-PASS $1"; }
fail() {
    echo "SMOKE-FAIL $1: $2"
    failures=$((failures + 1))
}

# 1. The sponsored gateway environment reached the container.
missing=()
[[ -n ${BOOLEY_GATEWAY_URL:-} ]] || missing+=("BOOLEY_GATEWAY_URL")
[[ -n ${BOOLEY_GATEWAY_TOKEN_COMMAND:-} ]] || missing+=("BOOLEY_GATEWAY_TOKEN_COMMAND")
[[ -n ${BOOLEY_GATEWAY_MODEL:-} ]] || missing+=("BOOLEY_GATEWAY_MODEL")
if ((${#missing[@]})); then
    fail gateway-env "missing ${missing[*]}"
else
    pass gateway-env
fi

# 1b. With no credential of its own, BOOLEY_AGENT_APP=auto (as shipped) chose
# Codex through the gateway. The registrar (postStartCommand) records the
# choice in ~/.booley-agent-app.json.
choice=$(python3 -c 'import json, pathlib; d = json.loads((pathlib.Path.home() / ".booley-agent-app.json").read_text()); print(d["app"], d["policy"], sep="|")' 2>&1)
if [[ ${BOOLEY_AGENT_APP:-} != auto || ${BOOLEY_PRIMARY_AUTH:-} != auto ]]; then
    fail agent-choice "expected BOOLEY_AGENT_APP=auto and BOOLEY_PRIMARY_AUTH=auto, got '${BOOLEY_AGENT_APP:-}' and '${BOOLEY_PRIMARY_AUTH:-}'"
elif [[ $choice != "codex|gateway" ]]; then
    fail agent-choice "auto chose '$choice', not codex|gateway"
else
    pass agent-choice
fi

# 2. No real agent credential is present, so only the gateway can answer.
present=()
for name in OPENAI_API_KEY CODEX_API_KEY ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN CLAUDE_CODE_OAUTH_TOKEN; do
    [[ -n ${!name:-} ]] && present+=("$name")
done
[[ -e $HOME/.codex/auth.json ]] && present+=("~/.codex/auth.json")
[[ -e $HOME/.claude/.credentials.json ]] && present+=("~/.claude/.credentials.json")
if ((${#present[@]})); then
    fail no-real-credential "found ${present[*]}"
else
    pass no-real-credential
fi

# 3. Doctor: exit 0 (no FAIL) and no agent.* WARN. Its gateway credential
# PASS is checked separately (doctor-gateway), so the negative run can show
# that Doctor itself noticed the missing gateway.
doctor_log="$evidence_dir/doctor.txt"
(cd "$project_root" && timeout 900 booley doctor) > "$doctor_log" 2>&1
doctor_status=$?
cat "$doctor_log"
if ((doctor_status != 0)); then
    fail doctor "booley doctor exited $doctor_status (FAIL lines: $(grep -c 'FAIL  ' "$doctor_log"))"
elif grep -E 'WARN  .*\[agent\.' "$doctor_log"; then
    fail doctor "agent credential WARN present"
else
    pass doctor
fi
if grep -q 'PASS  Codex auth: the gateway at ' "$doctor_log"; then
    pass doctor-gateway
else
    fail doctor-gateway "no gateway credential PASS line"
fi

# 4. One interactive Codex request, routed by the registrar-written provider,
# is answered by the stub. Without the gateway environment Codex would call
# OpenAI with no credential, so the request is not sent at all.
codex_log="$evidence_dir/codex.txt"
if ((${#missing[@]})); then
    fail codex-request "not sent: no gateway environment"
else
    (cd "$project_root" && timeout 180 codex exec "Reply with one word." < /dev/null) > "$codex_log" 2>&1
    codex_status=$?
    cat "$codex_log"
    if ((codex_status != 0)); then
        fail codex-request "codex exec exited $codex_status"
    elif ! grep -qx "$stub_reply" "$codex_log"; then
        fail codex-request "the stub's reply is not in Codex's output"
    else
        pass codex-request
    fi
fi

if ((failures)); then
    echo "sponsored smoke: $failures check(s) failed"
    exit 1
fi
echo "sponsored smoke: all checks passed"
