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

## About this demo

This is both a runnable Booley demo and a reference for configuring the
[YosysHQ/PicoRV32](https://github.com/YosysHQ/picorv32) RTL project.

Booley keeps its configuration in this separate repository. Setup adds only
ignored files and local guidance links to the PicoRV32 checkout; no tracked
upstream file is modified.

## Experiment with the demo

Open a new Codex or Claude Code terminal and experiment. Measure area and
performance, find critical paths, optimize the design, fix bugs, or add new
features and RISC-V extensions. Try making the CPU pipelined. See how far you
can push the models, the design, and Booley itself.

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
[CONFIG.md](https://github.com/boldaxolotl/booley/blob/main/docs/CONFIG.md).

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
