# Booley in GitHub Codespaces

This Codespace is a complete Booley setup for [PicoRV32](https://github.com/YosysHQ/picorv32),
a small open-source RISC-V CPU. Simulation, synthesis and waveform tools are
already installed. All you bring is a Claude account (a Claude subscription or
an Anthropic Console account) or a ChatGPT account for Codex.

The folder open on the left is the PicoRV32 source. Its `.booley` folder is
your copy of the Booley demo configuration.

When VS Code asks **Do you trust the authors of the files in this folder?**,
click **Trust Folder & Continue**. That turns on the Booley Dashboard and the
waveform viewer.

## 1. Sign in to your agent

Sign in to **one** agent. If both are signed in, Booley uses Claude Code.

### Claude Code

Open a terminal (`` Ctrl+` ``) and run:

```bash
BROWSER=none claude auth login
```

Open the link it prints, sign in, and copy the code the page it lands on
shows. Paste the whole code at the `Paste code here if prompted >` prompt and
press Enter. Use each link once: if sign-in fails, run the command again for a
fresh link. (`BROWSER=none` stops Claude Code from also opening a tab that
returns to a `localhost` address, which a browser Codespace can't reach.)

### Codex

Open a terminal (`` Ctrl+` ``) and run:

```bash
codex login --device-auth
```

Open the link it prints, sign in with your ChatGPT account, and enter the
one-time code it shows. Then switch Booley to Codex (it starts with Claude Code
when nothing is signed in):

```bash
python -m booley.harness.incontainer_register
```

Either sign-in lasts until the Codespace's container is rebuilt; stopping and
restarting the Codespace keeps it.

## 2. Check the setup

In the terminal:

```bash
booley doctor
```

No check should fail. Until you sign in, Doctor warns that the agent has no
credential. A few Codespaces-specific warnings are waived on purpose;
`.booley/doctor-waivers.toml` says why.

## 3. Ask the agent to run things

Start a chat with `booley` and try these, one at a time:

> Check the project status and explain the available Targets.

> Run the sim_core simulation and tell me whether it passed.

> Open the sim_core waveform and show me the first few instruction fetches
> on the memory interface.

> Synthesize synth_core and report its area and maximum clock frequency.

The agent runs Booley Flows for each request, so the answers come from real
tool runs rather than guesses. Waveforms open in the VaporView viewer, and the
Booley Dashboard tab shows runs as they happen.

## 4. Main event: add a RISC-V extension in Goal Mode

Now hand the agent a real CPU change: add the RISC-V Zbb bit-manipulation
extension (18 instructions such as `clz`, `cpop`, `rev8` and `rol`) to
PicoRV32. Goal Mode gives the agent Goals that only real tool results can
meet, and the `zbb` Goalset fixes them in advance:

- the lint, both bus regressions and a new "Zbb disabled" testbench pass;
- bug, testbench and spec reviews come back clean, the spec review judging
  the RTL against the ratified Zbb chapter in `.booley/specs/zbb.md`;
- synthesis grows by at most 11% in cells and 3% in critical path.

Create a separate worktree for the change, so `main` stays untouched:

```bash
booley worktree new zbb
```

Then start a chat with `booley` and ask:

> Use booley-goal in the zbb worktree with the zbb Goalset

The agent lists the eight Goals and asks you to confirm before it starts.
After that it works on its own: it writes the RTL, firmware test and
testbench, runs the Flows and reviews, and fixes what they find. Expect
about half an hour; it uses your Claude or ChatGPT plan's usage.

Follow along while it works:

- `booley goal status`, run in `.booley/worktrees/zbb`, lists each Goal as
  met or unmet with its latest evidence.
- The Booley Dashboard tab shows the same Goals and every Flow run live.

When every Goal is met, the agent finishes and gives you the path of the
**Review Package**: the diff against the starting commit, the evidence
behind each Goal, the review findings, and the Target changes (such as the
new `sim_zbb_disabled`). `booley goal status` in the worktree shows that path
again later. The work stays on its own Goal Branch; merging it is your call.

See the [demo README](README.md#then-try-goal-mode) for Goal Mode in general.

## Good to know

- This Codespace runs on your own GitHub account's Codespaces quota (free
  accounts get a monthly allowance) and your own Claude or ChatGPT account.
  Stop it from [github.com/codespaces](https://github.com/codespaces) when
  you're done. A stopped Codespace still uses storage; delete it when you no
  longer need it.
- Your PicoRV32 edits live in `/workspaces/picorv32` and survive a rebuild.
- To run Booley on your own machine instead, see the
  [demo README](README.md#quick-start).
