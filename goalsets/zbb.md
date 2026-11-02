# Goalset: zbb

The fixed Goals for the demo's headline Goal Mode change, adding RV32 Zbb to
PicoRV32 as described in `.booley/specs/zbb-design.md`. Enter Goal Mode with
this Goalset alone. Its Goals are fixed: use the Goal arguments below exactly
as written, with no placeholders to fill in and no Goals to add or drop.

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
