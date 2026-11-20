#!/usr/bin/env bash
# Recreate generated inputs in a fresh checkout, linked worktree, or the Git-less
# measurement checkout of `booley measure`.
set -euo pipefail

project_root="${BOOLEY_WORKTREE:-$(git rev-parse --show-toplevel)}"
cd "$project_root"

# Keep upstream PicoSoC cores out of Booley's core discovery without changing
# any tracked upstream file. The marker and local exclude are both repeatable.
touch picosoc/FUSESOC_IGNORE
# The measurement checkout has no .git, so there is no exclude file to update.
if exclude_file="$(git rev-parse --git-path info/exclude 2>/dev/null)"; then
    mkdir -p "$(dirname "$exclude_file")"
    if ! grep -qxF '/picosoc/FUSESOC_IGNORE' "$exclude_file" 2>/dev/null; then
        printf '%s\n' '/picosoc/FUSESOC_IGNORE' >> "$exclude_file"
    fi
fi

# Without the RISC-V toolchain the firmware images cannot be built. Skip them so
# Targets that do not read them (lint, synth) still work; a simulation Target
# that declares a missing image is refused with the path named.
if ! command -v riscv32-unknown-elf-gcc >/dev/null 2>&1; then
    echo "post-setup: riscv32-unknown-elf-gcc not found; skipping firmware builds" >&2
    exit 0
fi

# The upstream build produces the RV32IMC image used by sim_core and sim_wb.
make firmware/firmware.hex TOOLCHAIN_PREFIX=riscv32-unknown-elf-

# Dhrystone's upstream testbench leaves compression off, so build RV32IM.
# GNU89 and the warning overrides accommodate its K&R-era C sources.
make -C dhrystone dhry.hex \
    TOOLCHAIN_PREFIX=riscv32-unknown-elf- \
    CFLAGS="-MD -O3 -mabi=ilp32 -march=rv32im -DTIME -DRISCV -std=gnu89 -Wno-implicit-int -Wno-implicit-function-declaration -Wno-builtin-declaration-mismatch"
