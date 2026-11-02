#!/usr/bin/env bash
# Codespaces smoke checks, run inside the booted demo devcontainer.
#
# Covers what a visitor's first five minutes depend on: the Codespaces layout,
# the agent choice with no credential (Codex through the demo gateway), the
# agent Git identity, Doctor, the lint, simulation and synthesis Targets, and
# the switch to the visitor's own Codex or Claude account. Every check runs
# even after an earlier one fails, and each prints one "SMOKE-PASS <check>" or
# "SMOKE-FAIL <check>: <reason>" line. Exit 1 when any check failed.
#
# Usage: smoke.sh EVIDENCE_DIR
set -uo pipefail

evidence_dir=${1:?usage: smoke.sh EVIDENCE_DIR}
project_root=/workspaces/picorv32
mkdir -p "$evidence_dir"
# Keep the whole run as evidence too, even when the caller times out.
exec > >(tee -a "$evidence_dir/smoke.txt") 2>&1
failures=0

pass() { echo "SMOKE-PASS $1"; }
fail() {
    echo "SMOKE-FAIL $1: $2"
    failures=$((failures + 1))
}

# Run one command from the Project root, keep its output as evidence, and
# record a check from its exit status.
check_command() {
    local name=$1 limit=$2
    shift 2
    local log="$evidence_dir/$name.txt"
    (cd "$project_root" && timeout "$limit" "$@") > "$log" 2>&1
    local status=$?
    cat "$log"
    if ((status == 0)); then
        pass "$name"
    else
        fail "$name" "'$*' exited $status"
    fi
}

# 1. Layout: the Project is a real checkout and its .booley links to this repo.
repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
if [[ ! -d $project_root/.git ]]; then
    fail layout "$project_root is not a Git checkout"
elif [[ "$(readlink -f "$project_root/.booley")" != "$(readlink -f "$repo_dir")" ]]; then
    fail layout "$project_root/.booley does not link to $repo_dir"
else
    pass layout
fi

# The start's BOOLEY_AGENT_APP=auto choice as "app|policy", from the record the
# registrar publishes on every start (and on each manual re-run).
choice_file="$HOME/.booley-agent-app.json"
read_choice() {
    python3 -c 'import json, sys; d = json.load(open(sys.argv[1])); print(d["app"], d["policy"], sep="|")' "$choice_file" 2>&1
}

# 2. Sponsored mode: with no credential of the visitor's own, BOOLEY_AGENT_APP=auto
# resolves to Codex through the demo gateway. The choice comes from the
# gateway settings alone: no demo token exists yet (the visitor claims one with
# booley-demo-claim), and none is needed to choose.
if [[ ${BOOLEY_AGENT_APP:-} != auto ]]; then
    fail agent-choice "BOOLEY_AGENT_APP is '${BOOLEY_AGENT_APP:-}', not auto"
elif ! choice=$(read_choice); then
    fail agent-choice "no readable choice record at $choice_file: $choice"
elif [[ $choice != "codex|gateway" ]]; then
    fail agent-choice "expected codex|gateway, got: $choice"
else
    pass agent-choice
fi

# The demo sign-in command: on-create sources shell-path.sh from ~/.bashrc,
# which puts booley-demo-claim on an interactive shell's PATH.
claim=$(bash -ic 'command -v booley-demo-claim' < /dev/null 2>&1)
hook="$repo_dir/.devcontainer/gateway/shell-path.sh"
if ! grep -qxF "[ -f \"$hook\" ] && source \"$hook\"" "$HOME/.bashrc"; then
    fail claim-on-path "~/.bashrc does not source .devcontainer/gateway/shell-path.sh"
elif [[ $claim != */.devcontainer/gateway/bin/booley-demo-claim ]]; then
    fail claim-on-path "booley-demo-claim is not on an interactive shell's PATH: $claim"
else
    pass claim-on-path
fi

# A visitor who signs in to Claude Code instead opens it without its first-run
# theme and auto-mode prompts (on-create records both as answered), so they go
# straight to `claude auth login`.
if python3 -c 'import json, pathlib, sys; c = json.loads((pathlib.Path.home() / ".claude.json").read_text()); sys.exit(0 if c.get("hasCompletedOnboarding") is True and c.get("theme") and c.get("hasSeenAutoDefaultNudge") is True else 1)' 2>/dev/null; then
    pass claude-onboarding
else
    fail claude-onboarding "~/.claude.json does not mark onboarding and the auto-mode nudge done"
fi

# 3. Agent commits use the [agent.git] identity, not one the platform injects.
ident=$(git -C "$project_root" var GIT_AUTHOR_IDENT 2>&1)
if [[ $ident == "Dev <dev@localhost> "* ]]; then
    pass git-identity
else
    fail git-identity "author identity is '$ident'"
fi

# 4. First-start setup a visitor relies on before running Doctor: agents find
# the Project guidance, and the editor extension may open the Dashboard.
missing_links=()
for name in AGENTS.md CLAUDE.md; do
    [[ "$(readlink -f "$project_root/$name")" == "$(readlink -f "$repo_dir/AGENTS.md")" ]] || missing_links+=("$name")
done
if ((${#missing_links[@]})); then
    fail agent-guidance "not linked to .booley/AGENTS.md: ${missing_links[*]}"
else
    pass agent-guidance
fi
policy=$(cd "$project_root" && booley dashboard --attach-policy 2>&1)
if python3 -c 'import json, sys; sys.exit(0 if json.loads(sys.argv[1])["enabled"] else 1)' "$policy" 2>/dev/null; then
    pass dashboard-task
else
    fail dashboard-task "attach policy: $policy"
fi

# 5. Doctor, before and after the demo sign-in, then the Targets a visitor
# tries first.
#
# Before the claim: Doctor runs the gateway token command fresh, and with no
# token yet it grades the gateway credential (check id agent.credential-missing).
# The pinned Booley FAILs it (FAIL lines print no id, so the smoke matches the
# message); newer Booley warns instead (the warning allowlist below names the
# id). CODESPACES.md tells visitors the check fails until they have a token.
# The smoke accepts that one finding, requires a finished Doctor run, and
# fails on anything else.
check_doctor() {
    local name=$1 log="$evidence_dir/$1.txt"
    (cd "$project_root" && timeout 900 booley doctor) > "$log" 2>&1
    local status=$?
    cat "$log"
    return $status
}
check_doctor doctor-before-claim
before_status=$?
other_fails=$(grep -E 'FAIL  ' "$evidence_dir/doctor-before-claim.txt" | grep -vF 'FAIL  BOOLEY_GATEWAY_TOKEN_COMMAND exited 1')
if (( before_status > 1 )) || ! grep -qE '[0-9]+ passed,' "$evidence_dir/doctor-before-claim.txt"; then
    fail doctor-before-claim "'booley doctor' did not finish (exit $before_status, no summary line)"
elif [[ -n $other_fails ]]; then
    fail doctor-before-claim "Doctor FAILs other than the missing demo token: $other_fails"
else
    pass doctor-before-claim
fi

# After the claim: a placeholder token in the file token.sh reads stands in for
# booley-demo-claim (Doctor only runs the command; no request reaches the
# gateway). Doctor then reports no FAIL and passes the gateway credential. The
# token goes again right after, so the later checks see a visitor who has not
# claimed one.
demo_token="$HOME/.config/booley-demo/token"
if [[ -e $demo_token ]]; then
    fail doctor "$demo_token already exists; refusing to overwrite it"
else
    mkdir -p "$(dirname "$demo_token")"
    printf 'bgw_smoke-placeholder-0123456789abcdef\n' > "$demo_token"
    check_doctor doctor
    after_status=$?
    if (( after_status != 0 )); then
        fail doctor "'booley doctor' with a demo token exited $after_status"
    elif ! grep -q 'PASS  Codex auth: the gateway at ' "$evidence_dir/doctor.txt"; then
        fail doctor "no PASS line for the gateway credential"
    else
        pass doctor
    fi
    rm -f "$demo_token"
fi
# Expected warnings, by exact check id. A Codespace on main has a local main
# branch; a CI checkout of a pull request does not. agent.credential-missing is
# the missing demo token in newer Booley (the "after" run must PASS it above).
expected_warnings='project-data\.destination-branch-missing|agent\.credential-missing'
unexpected=$(grep -hE 'WARN  ' "$evidence_dir/doctor-before-claim.txt" "$evidence_dir/doctor.txt" | grep -vE "\[($expected_warnings)[]:]")
if [[ -n $unexpected ]]; then
    fail doctor-warnings "unexpected Doctor warnings: $unexpected"
else
    pass doctor-warnings
fi
check_command targets 300 booley targets
check_command lint 600 booley flow lint --target lint_core
check_command sim 1200 booley flow sim --target sim_core
check_command synth 1200 booley flow synth --target synth_core
# The Goalsets parse with this image's Booley, and Goal Mode entry accepts the
# zbb Goals (spec file and synthesis baseline present) in this checkout.
check_command goalsets 300 env GOALSET_CHECK_REQUIRE_BOOLEY=1 PICORV32_ROOT="$project_root" \
    python3 -m pytest -q -p no:cacheprovider "$repo_dir/tests/ci/test_goalsets.py"

# 6. The own-account paths in CODESPACES.md: a visitor's own credential beats
# the gateway once the registrar re-runs. Placeholder login files stand in for
# `codex login --device-auth` and `claude auth login`; no request is sent.
# Each case checks the published choice (the gateway policy gives way to the
# shipped BOOLEY_PRIMARY_AUTH=auto) and the app `booley chat` starts, since
# Codex alone would start in sponsored mode too.
register() {
    (cd "$project_root" && python -m booley.harness.incontainer_register) >> "$evidence_dir/own-account-register.txt" 2>&1
}
# own_account_case NAME EXPECTED_CHOICE CHAT_MARKER
own_account_case() {
    local name=$1 expected=$2 marker=$3 got launched
    register
    got=$(read_choice)
    launched=$(cd "$project_root" && timeout 60 booley chat -- --version 2>&1)
    echo "$launched" > "$evidence_dir/$name-chat.txt"
    if [[ $got != "$expected" ]]; then
        fail "$name" "expected choice $expected after re-registering, got: $got"
    elif [[ $launched != *"$marker"* ]]; then
        fail "$name" "booley chat did not start the expected app: $launched"
    else
        pass "$name"
    fi
}
codex_auth="$HOME/.codex/auth.json"
claude_auth="$HOME/.claude/.credentials.json"
if [[ -e $codex_auth || -e $claude_auth ]]; then
    fail own-account "an agent login file already exists; refusing to overwrite it"
else
    mkdir -p "$(dirname "$codex_auth")" "$(dirname "$claude_auth")"
    # Codex login: Codex with the visitor's account, not the gateway.
    printf '{"tokens":{"access_token":"smoke-placeholder","refresh_token":"smoke-placeholder"}}\n' > "$codex_auth"
    own_account_case codex-switch "codex|auto" "codex-cli "
    # Claude login as well: Claude wins over Codex ("if both are signed in, it
    # picks Claude Code").
    printf '{"claudeAiOauth":{"accessToken":"smoke-placeholder","refreshToken":"smoke-placeholder"}}\n' > "$claude_auth"
    own_account_case claude-switch "claude|auto" "(Claude Code)"
    # Both logins gone: the next registration falls back to the gateway.
    rm -f "$codex_auth" "$claude_auth"
    register
    got=$(read_choice)
    if [[ $got == "codex|gateway" ]]; then
        pass gateway-fallback
    else
        fail gateway-fallback "expected codex|gateway after removing the logins, got: $got"
    fi
fi

if ((failures)); then
    echo "codespaces smoke: $failures check(s) failed"
    exit 1
fi
echo "codespaces smoke: all checks passed"
