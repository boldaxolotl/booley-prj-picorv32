# Goalset: zbb

The demo's headline Goal Mode change: add the ratified RV32 Zbb 1.0
bit-manipulation extension to PicoRV32. Enter Goal Mode with this Goalset
alone. Its Goals are fixed: use the Goal arguments below exactly as written,
with no placeholders to fill in and no Goals to add or drop.

## The change

Implement RV32 Zbb 1.0 as an internal PCPI co-processor,
`picorv32_pcpi_zbb`, in `picorv32.v`. It supports all 18 RV32 Zbb
instructions with their standard encodings: `andn`, `orn`, `xnor`, `clz`,
`ctz`, `cpop`, `max`, `maxu`, `min`, `minu`, `sext.b`, `sext.h`, `zext.h`,
`rol`, `ror`, `rori`, `orc.b` and `rev8`. The spec is
`.booley/specs/zbb.md`, an excerpt of the ratified Zbb chapter of the
unprivileged ISA manual shipped in the Sandbox image.

- A new `ENABLE_ZBB` parameter, default `0`, on `picorv32`, `picorv32_axi`
  and `picorv32_wb`. No external port changes.
- With Zbb enabled, each recognized instruction completes through the
  existing internal PCPI arbitration with a registered, fixed one-cycle
  response. It must not disturb the M-extension PCPI units or an external
  PCPI co-processor.
- Several Zbb encodings overlap base ALU opcode classes (`OP`, `OP-IMM`).
  The base decoder must route them to the co-processor rather than execute
  them as base instructions.
- With Zbb disabled, the same encodings take the existing illegal-instruction
  trap, and RV32IMC behavior is unchanged.

Verification the change adds:

- A directed Zbb firmware test that covers every instruction above,
  including boundary operands: zero inputs to `clz`, `ctz` and `cpop`,
  rotate amounts 0 and 31, and signed/unsigned min/max across the sign
  boundary. It runs with Zbb enabled on both bus testbenches, so `sim_core`
  (plain and AXI) and `sim_wb` exercise it.
- A self-checking `testbench_zbb_disabled.v` that executes a valid Zbb
  encoding with Zbb disabled and passes only on the expected
  illegal-instruction trap, plus a new `sim_zbb_disabled` Target for it in
  `.booley/cores/picorv32_sim.core` and `.booley/tests.toml`.
- `synth_core` builds with `ENABLE_ZBB=1`, so the synthesis Goal measures
  the cost of Zbb against the RV32IMC base.

This change may edit the upstream testbenches, `Makefile`, firmware and
tests, and the Project's cores, `tests.toml` and post-setup hook. Commit
both repositories in the worktree (the upstream checkout and its `.booley`)
before finishing.

## Goals

- `LINT:lint_core`: the AXI wrapper lints clean.
- `SIM:sim_core`, `SIM:sim_wb`: the plain/AXI and Wishbone regressions,
  including the Zbb test, pass.
- `SIM:sim_zbb_disabled`: the disabled-mode trap testbench passes. The
  change creates this Target.
- `REVIEW:rtl_bugs`, `REVIEW:tb_quality`, `REVIEW:rtl_spec`: each review
  finishes `clean` (no open findings). The spec review judges `picorv32.v`
  against `.booley/specs/zbb.md`.
- `SYNTH:synth_core`: Zbb costs at most 11% more cells and at most 3% more
  critical-path delay than `synth_core` at the Goal base commit.

## Goal arguments

```json
[
  {
    "family": "LINT",
    "target": "lint_core",
    "origin": "zbb"
  },
  {
    "family": "SIM",
    "target": "sim_core",
    "origin": "zbb"
  },
  {
    "family": "SIM",
    "target": "sim_wb",
    "origin": "zbb"
  },
  {
    "family": "SIM",
    "target": "sim_zbb_disabled",
    "origin": "zbb"
  },
  {
    "family": "REVIEW",
    "review": "rtl_bugs",
    "verdict": "clean",
    "paths": [
      "picorv32.v"
    ],
    "origin": "zbb"
  },
  {
    "family": "REVIEW",
    "review": "tb_quality",
    "verdict": "clean",
    "paths": [
      "testbench.v",
      "testbench_wb.v",
      "testbench_zbb_disabled.v"
    ],
    "origin": "zbb"
  },
  {
    "family": "REVIEW",
    "review": "rtl_spec",
    "verdict": "clean",
    "spec": ".booley/specs/zbb.md",
    "paths": [
      "picorv32.v"
    ],
    "origin": "zbb"
  },
  {
    "family": "SYNTH",
    "target": "synth_core",
    "thresholds": {
      "cell_count_increase_at_most": "11%",
      "critical_path_ps_increase_at_most": "3%"
    },
    "origin": "zbb"
  }
]
```
