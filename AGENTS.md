# AGENTS.md

## Project boundaries

- `picorv32.v` contains the design. Unless a ticket says otherwise, treat the
  upstream cores, subprojects, scripts, firmware, and tests as read-only.
- Keep Booley-owned files under `.booley_project/`. Root `AGENTS.md` and
  `CLAUDE.md` are ignored local links; never commit Booley artifacts or EDA
  output to the upstream repository.
- Do not remove `picosoc/FUSESOC_IGNORE`; it prevents discovery of upstream
  PicoSoC cores.

## Setup and verification

- In every fresh checkout or worktree, run
  `bash .booley_project/hooks/post-setup.sh` before simulation. Do not commit
  the generated firmware images.
- The Booley endpoints below exist **only inside the Session Runtime** (this Project's devcontainer). They are **MCP tools, not CLI programs**: check for them in your own MCP tool list, never with `command -v booley_status` / `which` / `booley_status --help`. A `$PATH` probe always comes back empty and will make you wrongly conclude the MCP tools are missing. If your harness hides MCP tools behind a code-mode sandbox, the list is `ALL_TOOLS` — search it for `mcp__booley__booley_status`.
- At the start of an Interactive Mode tab, call `booley_status` and show its
  status block.
- Discover Targets with Booley instead of maintaining or relying on a Target
  list here. Use Booley Flows for RTL feedback and `booley shell -- <command>`
  for an explicitly requested one-off toolchain command.
- If the Booley MCP tools are unavailable, reopen the project in its container
  or run `booley session up && booley session enter`; do not substitute raw
  host EDA commands.

## Other revisions

- Create additional checkouts with Booley's worktree helper, not bare Git
  worktrees or copied/symlinked live Booley state. Run the copied post-setup
  hook with `BOOLEY_WORKTREE` set to the new root, and pass that root as
  `work_dir` to Booley tools.
- For QoR comparisons against an earlier commit, prefer the Flow's `baseline`
  argument.
