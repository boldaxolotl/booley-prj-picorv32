---
summary: Add opt-in RV32 Zbb PCPI co-processor
type: feature
branch: main
base_sha: a473fc8fca393771d83b0ffcf0b14db3393339d8
scope:
  - picorv32.v
  - testbench.v
  - testbench_wb.v
  - testbench_zbb_disabled.v [new]
  - Makefile
  - tests/zbb.S [new]
  - .booley_project/cores/picorv32_sim.core
  - .booley_project/tests.toml
  - .booley_project/hooks/post-setup.sh
spec: /opt/riscv-docs/riscv-isa-manual.html
on_success:
  destination: review
  merge: true
  cleanup: true
  triage_report: true
priority: medium
created: "2026-08-07T15:25:47Z"
criteria:
  mandatory:
    lint_clean: [lint_core]
    sim_pass:
      - testbench.v @ sim_core @ main @ pass -> pass
      - testbench.v @ sim_core @ axi @ pass -> pass
      - testbench_wb.v @ sim_wb @ wb @ pass -> pass
      - testbench_zbb_disabled.v @ sim_zbb_disabled @ zbb_disabled @ pass -> pass
    review_rtl_bugs_done: true
    review_tb_quality_done: true
    synthesis_ok:
      targets: [synth_core]
      cell_count_increase_at_most: 11
      critical_path_ps_increase_at_most: 3
  optional:
    review_rtl_spec_done: true
    mutation_score: "14/15"
---

## Description

### Current State

PicoRV32 implements internal PCPI multiplier and divider units in `picorv32.v`, with arbitration in the core. The AXI4-Lite and Wishbone wrappers forward core configuration parameters. The existing self-checking firmware regressions cover the plain/AXI and Wishbone paths. No Zbb support, disabled-mode testbench, Zbb-specific Target, or enabled-mode QoR configuration exists.

### Required Changes

Implement ratified RV32 Zbb 1.0 as an internal `picorv32_pcpi_zbb` co-processor using standard instruction encodings. Support ANDN, ORN, XNOR, CLZ, CTZ, CPOP, MIN, MINU, MAX, MAXU, SEXT.B, SEXT.H, ZEXT.H, ROL, ROR, RORI, ORC.B, and REV8.

Expose an `ENABLE_ZBB` parameter, defaulting to `0`, through the core and both wrappers. When enabled, recognized Zbb instructions must complete through PCPI with a registered fixed one-cycle response. When disabled, the same encodings must remain unsupported and take the existing illegal-instruction trap path.

Update native decode/trap handling so standard Zbb encodings that overlap base ALU opcode classes are routed to PCPI rather than accepted as base instructions. Preserve RV32IMC behavior when Zbb is disabled.

Add a directed Zbb assembly regression, build it with Zbb assembler support, and run it on both existing bus testbenches. Add a standalone self-checking disabled-mode testbench that executes a valid Zbb encoding with Zbb disabled and passes only on the expected illegal-instruction trap, along with a `sim_zbb_disabled` Target for it. Configure `synth_core` with Zbb active for the QoR comparison.

### Affected Interfaces

`ENABLE_ZBB` is a new opt-in public parameter on `picorv32`, `picorv32_axi`, and `picorv32_wb`. No external PCPI ports change. The ticket adds a `sim_zbb_disabled` Target for the new standalone testbench.

## Implementation Plan

### Approach

Add a `picorv32_pcpi_zbb` module in the flat RTL source and integrate it into existing internal PCPI arbitration. Decode only ratified RV32 Zbb encodings, hold/complete via the standard PCPI protocol, and return one registered result cycle after acceptance. Keep the parameter disabled by default; test and `synth_core` configurations explicitly enable it.

### Implementation Steps

1. Add `ENABLE_ZBB` parameter plumbing to the core and AXI/Wishbone wrappers.
2. Implement Zbb decode, result logic, PCPI handshake, and arbitration in `picorv32.v`; adjust base decoder classification so Zbb encodings reach PCPI.
3. Enable Zbb in the AXI/plain and Wishbone regression instantiations while retaining the default parameter value of zero.
4. Add `tests/zbb.S`, covering every RV32 Zbb instruction and specified boundary operands; update build and post-setup inputs to assemble and stage it.
5. Add `testbench_zbb_disabled.v` and its `sim_zbb_disabled` Target, checking that a valid Zbb word traps when disabled.
6. Configure `synth_core` with Zbb active and enforce the QoR thresholds.

### Interface Changes

New `ENABLE_ZBB` boolean parameter, default `0`, propagated through all public wrappers. Internal PCPI wires connect the new co-processor; no external port changes.

### Edge Cases & Risks

Count operations must return 32 for zero inputs where specified. Rotate amounts use RV32 low five-bit semantics, including 0 and 31. Signed/unsigned min/max must differ correctly at sign boundaries. Byte/halfword extensions, `orc.b`, and `rev8` require exact lane behavior. Zbb priority/arbitration must not interfere with M-extension PCPI units or external PCPI use.

### Verification

Run all enabled-mode regressions on plain, AXI, and Wishbone paths; run the disabled-mode trap regression; lint the wrapper; review RTL bugs, specification compliance, and testbench quality; synthesize the Zbb-enabled top-level core with no more than 11% cell-count growth and no more than 3% critical-path increase; require mutation score at least 14/15.

### Open Questions

None.
