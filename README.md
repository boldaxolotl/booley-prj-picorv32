# PicoRV32 Booley demo

## Try it in your browser

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/boldaxolotl/booley-prj-picorv32?quickstart=1)

One click gives you a running Booley with PicoRV32 in browser VS Code: no
local install, macOS and Windows included. It's free: the 4-core Codespace
runs on your own GitHub account's free monthly Codespaces quota (about 30
hours a month on a free account), and the agent runs GPT-6 Luna on the Booley
maintainer's account after a GitHub sign-in. You can run it on your own
ChatGPT account instead, and chat with Claude Code on your own Claude
account. The first launch takes 3-4 minutes while the container image builds. [START-HERE.md](START-HERE.md) opens automatically
and walks you through signing in, then sends you to [Try the demo](#try-the-demo).

## Quick start (local install)

This section installs Booley on your own machine. In a Codespace, everything
is already installed: skip to [Try the demo](#try-the-demo).

Needs Booley 0.5.0 or later.

[Install Booley](https://github.com/boldaxolotl/Booley#installation) (including `booley bootstrap`), then clone both repositories:

```bash
git clone https://github.com/YosysHQ/picorv32
cd picorv32
git clone https://github.com/boldaxolotl/booley-prj-picorv32 .booley
```

The demo's default Agent CLI is Codex, so sign in to Codex first
(`codex login`, or an OpenAI API key in your shell). Claude Code is listed too:
open it with `booley chat --cli claude`. To make it the default, set
`default = "claude"` in `[agent]` of `.booley/booley.toml` before
initialization.

Initialize the project on the host:

```bash
booley init
```

`booley init` replaces the demo's `auth = "visitor"` in
`.booley/booley.toml` with your agent sign-in choice, detected from your own
logins. (`visitor` is the demo Codespace's setting.) Review the change and
commit it in the `.booley` checkout:

```bash
git -C .booley diff
git -C .booley commit -am "Record my Booley agent setup"
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

There shouldn't be any Doctor warnings. The demo sets `[sandbox] memory =
"8g"`, which fits the 16 GB demo Codespace and most laptops. If Doctor warns
that `[sandbox].memory` plus swap is more than your machine has, lower
`memory` in `.booley/booley.toml`. For any other warning, use the
`/booley-heal` skill.

## Try the demo

Run Flows one at a time, hand the agent the prepared Zbb change, then
experiment on your own. In a Codespace, finish steps 1 and 2 of
[START-HERE.md](START-HERE.md) first.

### 1. Ask the agent to run things

Start a chat with `booley` and try these, one at a time:

> Check the project status and explain the available Targets.

> Run the sim_core simulation.

> Open the sim_core waveform and show me the first few instruction fetches
> on the memory interface.

> Synthesize synth_core and report its area and maximum clock frequency.

The agent runs Booley Flows for each request, so the answers come from real
tool runs rather than guesses. Waveforms open in the VaporView viewer, and the
Booley Dashboard tab shows runs as they happen.

### 2. Main event: add a RISC-V extension and measure it

Now hand the agent a real CPU change: add the RISC-V Zbb bit-manipulation
extension (18 instructions such as `clz`, `cpop`, `rev8` and `rol`) to
PicoRV32. What to build, and which tests to add, is in the design file
`.booley/specs/zbb-design.md`.

You accept the change by its numbers, not by the agent's word. The demo's
`.booley/metrics.toml` fixes them in advance: `lint_core` lints with no
error, every simulation test passes, and `synth_core` reports its area and
timing. Booley's own code runs the measurement, not the agent: every Flow,
in a clean checkout of the commit, the same way each time.

Start a chat with `booley` and ask:

> Create a zbb worktree and implement the design in
> .booley/specs/zbb-design.md. Zbb may cost at most 11% more cells and 5%
> more critical-path delay on synth_core. Measure the base first, then give
> me a Measured Commit.

The agent creates the worktree first, so `main` stays untouched. Then it
works on its own: it writes the RTL, firmware test and testbench, runs the
Flows, and fixes what they find. When a bound is unmet, it fixes the design
and measures again. Expect about half an hour of your agent's usage: the demo
allowance in a Codespace, or your own ChatGPT or Claude plan.
<!-- TODO(#4982): replace "half an hour" with the measured 0.5.0 run time. -->

Follow along on the Booley Dashboard tab: the Sessions window shows the
agent's session, with a `measuring` line under it while a measurement
runs, and the Jobs window lists every Flow run.

At the end the agent gives you the **Measurement Report**: a verdict line,
each metric with its value and bound, and a Δ column against the base. A
green header means every bound is met and the commit is Measured. The
Δ column is where you check the 11% and 5%. On the Dashboard, `Enter` on the
session's measurement line opens the same report.

To have the RTL checked against the ratified Zbb chapter as well, ask:

> Check picorv32.v against .booley/specs/zbb.md.

The Reviewer reports what the RTL does that the spec doesn't ask for, or
misses, and the agent fixes the findings you choose.

The work stays on the worktree's own branch; merging it is your call.

See [Metric-Driven Development](https://github.com/boldaxolotl/Booley/blob/main/docs/user/METRIC-DRIVEN-DEVELOPMENT.md)
in the Booley docs for writing `metrics.toml`, relative targets and reading
the report.

### 3. Build whatever you want

Some ideas to try next:

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
point the agent at it, as the Zbb change does.

## About this demo

The demo IP is [PicoRV32](https://github.com/YosysHQ/picorv32), Claire Wolf's
open-source RISC-V CPU core. Its small, area-optimized, straightforward
multi-cycle architecture keeps the RTL approachable and lint, simulation, and
synthesis runs fast while still exercising Booley on a real design.

This repository is both a runnable Booley demo and a reference for configuring
Booley projects.

Booley keeps its configuration in this separate repository. Setup adds only
ignored files and local guidance links to the PicoRV32 checkout; no tracked
upstream file is modified. In this repository, your `.booley` clone, setup
records only your agent sign-in choice, which the Quick start has you commit.

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
