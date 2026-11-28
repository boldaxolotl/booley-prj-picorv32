# AGENTS.md

## Project boundaries

- `picorv32.v` contains the design. Unless the user says otherwise, treat the
  upstream cores, subprojects, scripts, firmware, and tests as read-only.
- Keep Booley-owned files under `.booley/`. Root `AGENTS.md` and
  `CLAUDE.md` are ignored local links; never commit Booley artifacts or EDA
  output to the upstream repository.
- Do not remove `picosoc/FUSESOC_IGNORE`; it prevents discovery of upstream
  PicoSoC cores.

## Setup and verification

- In the main checkout, run `bash .booley/hooks/post-setup.sh` before
  simulation; `booley worktree prepare` runs it in a worktree. Do not commit
  the generated firmware images.
- The Booley endpoints below exist **only inside the Sandbox**. They are **MCP tools, not CLI programs**: check for them in your own MCP tool list, never with `command -v booley_status` / `which` / `booley_status --help`. A `$PATH` probe always comes back empty and will make you wrongly conclude the MCP tools are missing. If your harness hides MCP tools behind a code-mode sandbox, the list is `ALL_TOOLS` — search it for `mcp__booley__booley_status`.
- At the start of a thread, call `booley_status` and show its
  status block.
- Discover Targets with Booley instead of maintaining or relying on a Target
  list here. Use Booley Flows for RTL feedback and `booley shell -- <command>`
  for an explicitly requested one-off toolchain command.
- If `booley_status` is absent from the MCP tool list, you are on the host.
  Point the user to a T3 Code thread: run `booley session up` on the host,
  open the pairing link it prints in a browser, and start a thread (or, for a
  shell in the Sandbox, run `booley session enter`); do not substitute raw
  host EDA commands.

## Other revisions

- Another branch or commit: work in a T3 Code thread's worktree, or make one
  with `git worktree add` and run `booley worktree prepare` in it before
  anything else; never copy `.booley/`. Pass that root as `work_dir` to
  Booley tools.
- For QoR comparisons against an earlier commit, prefer the Flow's `baseline`
  argument.
