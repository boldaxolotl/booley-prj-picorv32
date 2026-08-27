#!/usr/bin/env bash
# Recreate generated inputs in a fresh checkout or ticket worktree.
set -euo pipefail

project_root="${BOOLEY_WORKTREE:-$(git rev-parse --show-toplevel)}"
cd "$project_root"

# Keep upstream PicoSoC cores out of Booley's core discovery without changing
# any tracked upstream file. The marker and local exclude are both repeatable.
touch picosoc/FUSESOC_IGNORE
exclude_file="$(git rev-parse --git-path info/exclude)"
mkdir -p "$(dirname "$exclude_file")"
if ! grep -qxF '/picosoc/FUSESOC_IGNORE' "$exclude_file" 2>/dev/null; then
    printf '%s\n' '/picosoc/FUSESOC_IGNORE' >> "$exclude_file"
fi

# The upstream build produces the RV32IMC image used by sim_core and sim_wb.
make firmware/firmware.hex TOOLCHAIN_PREFIX=riscv32-unknown-elf-

# Dhrystone's upstream testbench leaves compression off, so build RV32IM.
# GNU89 and the warning overrides accommodate its K&R-era C sources.
make -C dhrystone dhry.hex \
    TOOLCHAIN_PREFIX=riscv32-unknown-elf- \
    CFLAGS="-MD -O3 -mabi=ilp32 -march=rv32im -DTIME -DRISCV -std=gnu89 -Wno-implicit-int -Wno-implicit-function-declaration -Wno-builtin-declaration-mismatch"
