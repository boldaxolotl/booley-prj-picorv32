# PicoRV32 Booley demo

## Try it in your browser

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/boldaxolotl/booley-prj-picorv32?quickstart=1)

One click gives you a running Booley with PicoRV32 in browser VS Code: no
local install, macOS and Windows included. It's free: the 4-core Codespace
runs on your own GitHub account's free monthly Codespaces quota (about 30
hours a month on a free account), and the agent runs GPT-6 Luna on the Booley
maintainer's account after a GitHub sign-in. You can use your own
Claude or ChatGPT account instead. The first launch takes 3-4 minutes while
the container image builds. [START-HERE.md](START-HERE.md) opens automatically
and walks you through signing in and the first five minutes.

## Quick start

Needs Booley 0.3.0 or later.

[Install Booley](https://github.com/boldaxolotl/Booley#installation) (including `booley bootstrap`), then clone both repositories:

```bash
git clone https://github.com/YosysHQ/picorv32
cd picorv32
git clone https://github.com/boldaxolotl/booley-prj-picorv32 .booley
```

The default agent provider is Claude Code. To use Codex, add
`[agent] provider = "codex"` to `.booley/booley.toml` before initialization.

Initialize the project on the host:

```bash
booley init
```

Open the `picorv32` folder in VS Code. A popup notification should offer
**Reopen in Container**; choose it. If the popup does not appear, press `F1`
(or `Ctrl+Shift+P`), then run **Dev Containers: Reopen in Container** from the
Command Palette.

In a container terminal, build the generated firmware and run the deep Doctor
gate:

```bash
bash .booley/hooks/post-setup.sh
booley doctor --deep
```

There shouldn't be any Doctor warnings. If any appear, use the `/booley-heal`
skill to resolve them.

## Try the demo

The demo is the same here as in a Codespace (steps 3 to 5 of
[START-HERE.md](START-HERE.md)): run Flows one at a time, hand the agent the
prepared Zbb Goal, then experiment on your own.

### 1. Ask the agent to run things

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

### 2. Main event: add a RISC-V extension in Goal Mode

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

### 3. Build whatever you want

<!-- demo-flow:experiment (START-HERE.md and README.md share this text; tests/ci check it) -->
Some ideas to try next, in Interactive Mode or Goal Mode:

- Add a custom instruction, such as a one-cycle CRC-32 step, and firmware
  that uses it to checksum a buffer.
- Add a peripheral on the memory bus, such as a UART or a GPIO block, and
  firmware that drives it.
- Make the core smaller or faster.
- Strengthen the verification: more tests, coverage, or a stricter
  testbench.
- Delete PicoRV32 and build your own design from scratch. The agent updates
  the Targets in `.booley/cores` to match.

For a bigger change, write the design down in a Markdown file first and
point the agent at it, as the Zbb Goal does.
<!-- /demo-flow -->

## About this demo

The demo IP is [PicoRV32](https://github.com/YosysHQ/picorv32), Claire Wolf's
open-source RISC-V CPU core. Its small, area-optimized, straightforward
multi-cycle architecture keeps the RTL approachable and lint, simulation, and
synthesis runs fast while still exercising Booley on a real design.

This repository is both a runnable Booley demo and a reference for configuring
Booley projects.

Booley keeps its configuration in this separate repository. Setup adds only
ignored files and local guidance links to the PicoRV32 checkout; no tracked
upstream file is modified.

## Targets

| Target | Flow | Top | Configuration |
|---|---|---|---|
| `sim_core` | Verilator simulation | `picorv32_wrapper` | RV32IMC; `main` and randomized AXI tests |
| `sim_wb` | Verilator simulation | `picorv32_wrapper` | RV32IMC Wishbone regression |
| `sim_dhry` | Verilator simulation | `testbench` | RV32IM Dhrystone benchmark |
| `lint_core` | Verilator lint | `picorv32_axi` | RV32IMC wrapper |
| `synth_core` | Yosys + OpenROAD synthesis | `picorv32` | RV32IMC, 10 ns SDC |
| `fpga_core` | Vivado implementation | `picorv32_axi` | RV32IMC, Kintex-7 `xc7k70t-fbg676`, 10 ns XDC, out of context |

`testbench_ez.v` is intentionally excluded because it has no self-checking
verdict. The Dhrystone run is metric-based: completion is recognized by its
`DMIPS_Per_MHz:` score line rather than a self-checking pass message.

For a description of Booley's project configuration and files, see
[CONFIG.md](https://github.com/boldaxolotl/booley/blob/main/docs/user/CONFIG.md).

## Optional: make Vivado available

The host-provisioned Vivado flow itself is supported only on Linux x86-64.

The FPGA Target requires a Linux Vivado 2025.2 or later installation. The
`--source` path is the release root containing `Vivado/bin/vivado` and the
sibling `tps/` directory, not the `Vivado/` directory itself.

Register an installation once per host, then grant this exact project clone
access to it:

```bash
booley eda installation register vivado_2025_2 \
  --kind vivado \
  --source /path/to/Xilinx/2025.2

booley eda grant add "$PWD" \
  --kind vivado \
  --installation vivado_2025_2
```

The checked-in configuration leaves the FPGA Flow disabled and does not request
Vivado. To opt in, enable `[flows.fpga]` and add an `[eda.vivado]` block with
`provisioning = "host"`. Use the host registration and project grant above;
do not add host paths or license variables to the project configuration. A
floating-license profile, if required, is registered and granted separately by
the host administrator.
