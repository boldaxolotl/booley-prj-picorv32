# PicoRV32 Booley demo

## Quick start

Install the latest framework release, then clone both repositories:

```bash
git clone https://github.com/YosysHQ/picorv32
cd picorv32
git clone https://github.com/boldaxolotl/booley-prj-picorv32 .booley_project
```

The default agent provider is Codex. To use Claude, change `[agent].provider`
in `.booley_project/booley.toml` before initialization.

Initialize the project on the host:

```bash
booley init
```

Open the `picorv32` folder in VS Code and choose **Reopen in Container**. In a
container terminal, build the generated firmware and run the deep Doctor gate:

```bash
bash .booley_project/hooks/post-setup.sh
booley doctor --deep
```

There shouldn't be any Doctor warnings. If any appear, use the `/booley-heal`
skill to resolve them.

## Explore in Interactive Mode first

Start the Project's configured Codex or Claude Code chat from the container
terminal:

```bash
booley
```

Bare `booley` is the short form of `booley chat`; both open the provider
selected by `[agent].provider`. Then ask the agent to show how the project,
Targets, and Booley Flows fit together. For example:

> Check the PicoRV32 project status, explain the available Targets, then run a
> lint or simulation Flow and walk me through the result.

Interactive Mode is the easiest way to learn the demo: you choose each next
step and can ask questions as the agent inspects or runs the design.

## Then try Ticket Mode

The demo intentionally ships without pre-made Tickets. In a Codex or Claude
Code chat, ask the agent to use the `booley-ticket-create` skill for a change
you want to try. For example:

> Use the booley-ticket-create skill to make a detailed Ticket that adds a
> small, opt-in PicoRV32 feature and verifies its disabled behavior.

Ticket Mode is an optional next step. Ticket creation is part of that workflow:
the skill refines the idea, lets you
review the complete draft, and authors any required Target or control changes
in the Ticket's isolated workspace before enqueueing it. The configured `main`
branch therefore stays runnable and Doctor-clean while the Ticket is waiting.
Once the Ticket is enqueued, use the run-and-fix skill or `booley run` to
execute it.

## About this demo

This is both a runnable Booley demo and a reference for configuring the
[YosysHQ/PicoRV32](https://github.com/YosysHQ/picorv32) RTL project.

Booley keeps its configuration in this separate repository. Setup adds only
ignored files and local guidance links to the PicoRV32 checkout; no tracked
upstream file is modified.

## Experiment with the demo

Explore interactively first: measure area and performance, find critical paths,
or ask the agent to explain a configuration. Then create a Ticket when you want
Booley to pursue a well-defined change autonomously—optimize the design, fix a
bug, add a RISC-V extension, or even try making the CPU pipelined. See how far
you can push the models, the design, and Booley itself.

## Targets

| Target | Flow | Top | Configuration |
|---|---|---|---|
| `sim_core` | Icarus simulation | `testbench` | RV32IMC; `main` and randomized AXI tests |
| `sim_wb` | Icarus simulation | `testbench` | RV32IMC Wishbone regression |
| `sim_dhry` | Icarus simulation | `testbench` | RV32IM Dhrystone benchmark |
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
