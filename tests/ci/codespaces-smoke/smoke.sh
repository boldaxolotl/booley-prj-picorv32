#!/usr/bin/env bash
# Codespaces smoke checks, run inside the booted demo devcontainer.
#
# Covers what a visitor's first five minutes depend on: the Codespaces layout,
# the agent choice with no credential, the agent Git identity, Doctor, and the
# lint, simulation and synthesis Targets. Every check runs even after an
# earlier one fails, and each prints one "SMOKE-PASS <check>" or
# "SMOKE-FAIL <check>: <reason>" line. Exit 1 when any check failed.
#
# Usage: smoke.sh EVIDENCE_DIR
set -uo pipefail

evidence_dir=${1:?usage: smoke.sh EVIDENCE_DIR}
project_root=/workspaces/picorv32
mkdir -p "$evidence_dir"
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

# 2. With no credential, BOOLEY_AGENT_APP=auto resolves to Claude Code and
# offers its sign-in (the registrar publishes the choice on every start).
choice_file="$HOME/.booley-agent-app.json"
if [[ ${BOOLEY_AGENT_APP:-} != auto ]]; then
    fail agent-choice "BOOLEY_AGENT_APP is '${BOOLEY_AGENT_APP:-}', not auto"
elif ! choice=$(python3 -c 'import json, sys; d = json.load(open(sys.argv[1])); print(d["app"], "|", d["reason"])' "$choice_file" 2>&1); then
    fail agent-choice "no readable choice record at $choice_file: $choice"
elif [[ $choice != "claude |"* ]]; then
    fail agent-choice "expected claude, got: $choice"
else
    pass agent-choice
fi

# 3. Agent commits use the [agent.git] identity, not one the platform injects.
ident=$(git -C "$project_root" var GIT_AUTHOR_IDENT 2>&1)
if [[ $ident == "Dev <dev@localhost> "* ]]; then
    pass git-identity
else
    fail git-identity "author identity is '$ident'"
fi

# 4. Doctor reports no FAIL, then the Targets a visitor tries first pass.
check_command doctor 900 booley doctor
check_command targets 300 booley targets
check_command lint 600 booley flow lint --target lint_core
check_command sim 1200 booley flow sim --target sim_core
check_command synth 1200 booley flow synth --target synth_core

if ((failures)); then
    echo "codespaces smoke: $failures check(s) failed"
    exit 1
fi
echo "codespaces smoke: all checks passed"
