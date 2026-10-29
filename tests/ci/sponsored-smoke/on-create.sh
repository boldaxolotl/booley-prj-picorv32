#!/usr/bin/env bash
# onCreateCommand of the sponsored-mode CI smoke config.
#
# Builds the same layout as the demo's Codespaces config: /workspaces/picorv32
# is a pinned upstream PicoRV32 checkout (the workspace folder) and its .booley
# is a symlink to this repo's checkout. Then it builds the firmware images and
# fetches the Nangate45 PDK, so Doctor sees a complete Project.
set -euo pipefail
stamp() { echo "[on-create $(date -u +%H:%M:%S)] $*"; }

UPSTREAM_URL=https://github.com/YosysHQ/picorv32
UPSTREAM_REF=a473fc8fca393771d83b0ffcf0b14db3393339d8
PROJECT=/workspaces/picorv32
repo_dir="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"

# Append a line to a file only when it is not already present.
add_line() { grep -qxF "$2" "$1" 2>/dev/null || printf '%s\n' "$2" >> "$1"; }

stamp "clone upstream picorv32 into $PROJECT"
if [ ! -d "$PROJECT/.git" ]; then
    mkdir -p "$PROJECT"
    git -C "$PROJECT" init -q
    git -C "$PROJECT" remote add origin "$UPSTREAM_URL"
    git -C "$PROJECT" fetch -q --depth 1 origin "$UPSTREAM_REF"
    git -C "$PROJECT" checkout -q -B main FETCH_HEAD
fi

stamp "link Booley Directory $PROJECT/.booley -> $repo_dir"
ln -sfn "$repo_dir" "$PROJECT/.booley"
# Keep Booley's entry, generated projections, and the devcontainer spec out of
# upstream's git status.
for pattern in '/.booley' '/.booley-projected-*.core' '/.devcontainer'; do
    add_line "$PROJECT/.git/info/exclude" "$pattern"
done
for repo in "$PROJECT" "$repo_dir"; do
    git -C "$repo" config gc.worktreePruneExpire never
    git -C "$repo" config --local core.autocrlf false
    git -C "$repo" config --local worktree.useRelativePaths true
done
# The line-ending policy `booley init` writes for the Project checkout.
add_line "$PROJECT/.git/info/attributes" '* text=auto eol=lf'
mkdir -p "$repo_dir"/tickets/{board,state,logs,locks}

stamp "post-setup (firmware build)"
(cd "$PROJECT" && bash .booley/hooks/post-setup.sh)

stamp "fetch Nangate45 PDK into \$PRJ_LIB_DIR=${PRJ_LIB_DIR:-unset}"
python3 -c 'import os; from pathlib import Path; from booley.harness import nangate_pdk; print(nangate_pdk.fetch(Path(os.environ["PRJ_LIB_DIR"])))'
stamp "on-create done"
