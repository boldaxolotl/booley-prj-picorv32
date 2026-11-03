# Design: RV32 Zbb for PicoRV32

Add the ratified RV32 Zbb 1.0 bit-manipulation extension to PicoRV32. The
`zbb` Goalset (`.booley/goalsets/zbb.md`) holds the Goals that judge this
change.

## The change

Implement RV32 Zbb 1.0 as an internal PCPI co-processor,
`picorv32_pcpi_zbb`, in `picorv32.v`. It supports all 18 RV32 Zbb
instructions with their standard encodings: `andn`, `orn`, `xnor`, `clz`,
`ctz`, `cpop`, `max`, `maxu`, `min`, `minu`, `sext.b`, `sext.h`, `zext.h`,
`rol`, `ror`, `rori`, `orc.b` and `rev8`. Their semantics and encodings
are in `.booley/specs/zbb.md`, an excerpt of the ratified Zbb chapter of the
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

## Verification

The change adds:

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

## Scope

This change may edit the upstream testbenches, `Makefile`, firmware and
tests, and the Project's cores and `tests.toml`. Goal Mode protects the
post-setup hook, so put any Zbb build-flag change in the `Makefile` or the
test sources instead. Commit both repositories in the worktree (the upstream
checkout and its `.booley`) before finishing.
