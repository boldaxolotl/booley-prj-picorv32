#!/usr/bin/env bash
# onCreateCommand of the demo's GitHub Codespaces config.
#
# Layout: /workspaces/picorv32 is a pinned upstream PicoRV32 checkout and the
# folder the editor opens; its .booley entry is a symlink to this repository's
# Codespaces clone, so Booley state and edits land in the visitor's own copy of
# this repo. Both live under /workspaces, the only tree that survives a
# container rebuild, and onCreate re-runs after every rebuild, so every step
# below must be safe to repeat.
#
# Then build the firmware images (post-setup hook) and fetch the Nangate45 PDK
# into $PRJ_LIB_DIR, so simulation and ASIC synthesis work on first start.
set -euo pipefail
log="$HOME/on-create.log"
exec > >(tee -a "$log") 2>&1
stamp() { echo "[on-create $(date -u +%H:%M:%S)] $*"; }

UPSTREAM_URL=https://github.com/YosysHQ/picorv32
# The upstream revision this demo's cores and tests were written against.
UPSTREAM_REF=a473fc8fca393771d83b0ffcf0b14db3393339d8
PROJECT=/workspaces/picorv32
# This repository's checkout (the script lives in <repo>/.devcontainer/).
repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
started=$(date +%s)

# Append a line to a file only when it is not already present (rebuild-safe).
add_line() { grep -qxF "$2" "$1" 2>/dev/null || printf '%s\n' "$2" >> "$1"; }

# A checkout with a commit is the visitor's (a rebuild): keep it and any edits.
# Anything less is a first clone that was interrupted, so finish it.
if head=$(git -C "$PROJECT" rev-parse -q --verify HEAD 2>/dev/null); then
    stamp "keep existing $PROJECT checkout at ${head:0:7}"
else
    stamp "clone upstream PicoRV32 $UPSTREAM_REF into $PROJECT"
    mkdir -p "$PROJECT"
    git -C "$PROJECT" init -q
    git -C "$PROJECT" remote remove origin 2>/dev/null || true
    git -C "$PROJECT" remote add origin "$UPSTREAM_URL"
    git -C "$PROJECT" fetch -q --depth 1 origin "$UPSTREAM_REF"
    git -C "$PROJECT" checkout -q -B main FETCH_HEAD
fi

stamp "link Booley Directory $PROJECT/.booley -> $repo_dir"
ln -sfn "$repo_dir" "$PROJECT/.booley"
# Keep Booley's entry, generated core projections and the editor settings out
# of upstream's git status.
mkdir -p "$PROJECT/.git/info"
for pattern in '/.booley' '/.booley-projected-*.core' '/.devcontainer'; do
    add_line "$PROJECT/.git/info/exclude" "$pattern"
done
# The repository settings `booley init` applies to a Project and its Booley
# Directory: keep worktrees, LF line endings, and relocatable worktree links.
for repo in "$PROJECT" "$repo_dir"; do
    git -C "$repo" config gc.worktreePruneExpire never
    git -C "$repo" config --local core.autocrlf false
    git -C "$repo" config --local worktree.useRelativePaths true
done
add_line "$PROJECT/.git/info/attributes" '* text=auto eol=lf'
mkdir -p "$repo_dir"/tickets/{board,state,logs,locks}

stamp "build firmware images (post-setup hook)"
(cd "$PROJECT" && bash .booley/hooks/post-setup.sh)

stamp "fetch the Nangate45 PDK into PRJ_LIB_DIR=${PRJ_LIB_DIR:?PRJ_LIB_DIR is not set}"
python3 -c 'import os; from pathlib import Path; from booley.harness import nangate_pdk; print(nangate_pdk.fetch(Path(os.environ["PRJ_LIB_DIR"])))'

stamp "done in $(( $(date +%s) - started ))s"
