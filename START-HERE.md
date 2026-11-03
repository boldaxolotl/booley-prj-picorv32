# Booley in GitHub Codespaces

This Codespace is a complete Booley setup for [PicoRV32](https://github.com/YosysHQ/picorv32),
a small open-source RISC-V CPU. Simulation, synthesis and waveform tools are
already installed, and the agent is free: it runs OpenAI's GPT-6 Luna on the
Booley maintainer's account. You only need a GitHub account.

The Codespace itself runs on your GitHub account's free Codespaces quota:
about 30 hours a month of this 4-core Codespace. See
[GitHub's Codespaces billing](https://docs.github.com/en/billing/concepts/product-billing/github-codespaces).

The folder open on the left is the PicoRV32 source. Its `.booley` folder is
your copy of the Booley demo configuration.

## 1. Get your free demo token

Open a new terminal: press **Ctrl+Shift+`** (the backtick key, left of
**1**), or use the menu (☰) → **Terminal** → **New Terminal**. Run:

```bash
booley-demo-claim
```

Type `yes` to accept the notice. It then prints a GitHub link and a code
like `ABCD-1234`: open the link, enter the code, and click **Authorize**.
The terminal waits until you do, then prints **Done**. Your GitHub
account must be at least 30 days old. If it fails or the code expires, run it
again.

Each GitHub account gets $1 of demo usage per month. GPT-6 Luna is cheap, so
that's about 1.5 hours of the agent working nonstop, or about three runs of
the step 4 Goal (about $0.35 each). Normal back-and-forth use lasts longer. A
token lasts 30 days, and one GitHub account can hold 3 at a time.

Luna is a small model: capable enough for this demo, but not as strong as
Claude or the larger GPT models. For a stronger model, use your own account
(below).

### Or use your own Claude or ChatGPT account

Your own account gets you a stronger model, within your own plan's limits
instead of the demo allowance. Booley uses it instead of the demo token, so
skip `booley-demo-claim` and sign in:

**Claude Code.** Open a new terminal and run:

```bash
BROWSER=none claude auth login
```

Open the link it prints, sign in, and copy the code the page it lands on
shows. Paste the whole code at the `Paste code here if prompted >` prompt and
press Enter. Use each link once: if sign-in fails, run the command again for a
fresh link. (`BROWSER=none` stops Claude Code from also opening a tab that
returns to a `localhost` address, which a browser Codespace can't reach.)

**Codex.** Open a terminal and run:

```bash
codex login --device-auth
```

Open the link it prints, sign in with your ChatGPT account, and enter the
one-time code it shows.

Then switch Booley to your account (if both are signed in, it picks Claude
Code):

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

No check should fail once you have a demo token or have signed in; before
that, the agent credential check fails.

## 3. Ask the agent to run things

<!-- demo-flow:run-things (START-HERE.md and README.md share this text; tests/ci check it) -->
Start a chat with `booley` and try these, one at a time:

> Check the project status and explain the available Targets.

> Run the sim_core simulation.

> Open the sim_core waveform and show me the first few instruction fetches
> on the memory interface.

> Synthesize synth_core and report its area and maximum clock frequency.

The agent runs Booley Flows for each request, so the answers come from real
tool runs rather than guesses. Waveforms open in the VaporView viewer, and the
Booley Dashboard tab shows runs as they happen.
<!-- /demo-flow -->

## 4. Main event: add a RISC-V extension in Goal Mode

<!-- demo-flow:goal-mode (START-HERE.md and README.md share this text; tests/ci check it) -->
Now hand the agent a real CPU change: add the RISC-V Zbb bit-manipulation
extension (18 instructions such as `clz`, `cpop`, `rev8` and `rol`) to
PicoRV32. Goal Mode gives the agent Goals that only real tool results can
meet, and the `zbb` Goalset fixes them in advance:

- the lint, both bus regressions and a new "Zbb disabled" testbench pass;
- bug, testbench and spec reviews come back clean, the spec review judging
  the RTL against the ratified Zbb chapter in `.booley/specs/zbb.md`;
- synthesis grows by at most 11% in cells and 3% in critical path.

What to build, and which tests to add, is in the design file
`.booley/specs/zbb-design.md`.

Start a chat with `booley` and ask:

> Create a new zbb worktree and use /booley-goal with the zbb Goalset to
> implement the design described in .booley/specs/zbb-design.md

The agent creates the worktree first, so `main` stays untouched. Then it
lists the eight Goals and asks you to confirm before it starts. After that
it works on its own: it writes the RTL, firmware test and
testbench, runs the Flows and reviews, and fixes what they find. Expect
about half an hour of your agent's usage: the demo allowance in a Codespace,
or your own Claude or ChatGPT plan.

Follow along while it works:

- `booley goal status`, run in `.booley/worktrees/zbb`, lists each Goal as
  met or unmet with its latest evidence.
- The Booley Dashboard tab shows the same Goals and every Flow run live.

When every Goal is met, the agent finishes and gives you the path of the
**Review Package**: the diff against the starting commit, the evidence
behind each Goal, the review findings, and the Target changes (such as the
new `sim_zbb_disabled`). `booley goal status` in the worktree shows that path
again later. The work stays on its own Goal Branch; merging it is your call.

See [Goal Mode](https://github.com/boldaxolotl/Booley/blob/main/docs/user/USAGE.md#goal-mode)
in the Booley docs for Goalsets, threshold Goals, approvals and recovery.
<!-- /demo-flow -->

## 5. Build whatever you want

<!-- demo-flow:experiment (START-HERE.md and README.md share this text; tests/ci check it) -->
Some ideas to try next:

- Add another extension, such as Zba, Zbs, or an instruction of your own.
- Make the core smaller or faster.
- Strengthen the verification: more tests, coverage, or a stricter
  testbench.
- Delete PicoRV32 and build your own design from scratch. The agent updates
  the Targets in `.booley/cores` to match.

Each idea works like the Zbb Goal: ask for a new worktree and Goal Mode,
and say what you want. Pick the Goalset that fits from `.booley/goalsets/`
(`feature`, `bugfix`, `refactor` or `verification`), or ask for Goals of
your own. For example:

> Create a new zba worktree and use /booley-goal with the feature Goalset to
> add the RISC-V Zba extension to PicoRV32

For a bigger change, write the design down in a Markdown file first and
point the agent at it, as the Zbb Goal does.
<!-- /demo-flow -->

Long runs can use up the demo allowance quickly;
[sign in with your own account](#or-use-your-own-claude-or-chatgpt-account)
for more room.

## Good to know

- A running Codespace uses your quota (see the top of this page). Stop it from
  [github.com/codespaces](https://github.com/codespaces) when you're done. A
  stopped Codespace still uses storage; delete it when you no longer need it.
- The demo token's allowance resets each month. Rebuilding the container
  deletes the token; run `booley-demo-claim` to get a new one.
- Your PicoRV32 edits live in `/workspaces/picorv32` and survive a rebuild.
- To run Booley on your own machine instead, see the
  [demo README](README.md#quick-start).
