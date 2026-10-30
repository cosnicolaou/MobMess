#!/bin/bash
set -euo pipefail

# Locate mobmess executable
if command -v mobmess >/dev/null 2>&1; then
    MOBMESS_CMD="mobmess"
elif [ -x "/opt/homebrew/Caskroom/miniforge/base/envs/mobmess-py313/bin/mobmess" ]; then
    MOBMESS_CMD="/opt/homebrew/Caskroom/miniforge/base/envs/mobmess-py313/bin/mobmess"
elif command -v conda >/dev/null 2>&1; then
    MOBMESS_CMD="conda run -n mobmess-py313 mobmess"
else
    MOBMESS_CMD="python -m mobmess.mobmess_script"
fi

# Run mobmess systems using MUMmer4 --batch mode
# --batch 1000000000 (1GB chunks) prevents single-threaded suffix array sorting
# from hitting worst-case O(N^2) memory/sorting traps on large plasmid FASTA files.
${MOBMESS_CMD} systems \
    --sequences "$HOME/01_mobmess/all_plasx_clean.fasta" \
    --complete "$HOME/01_mobmess/all_plasx_circular.txt" \
    --output ./all_plasx-mobmess \
    --threads "${THREADS:-32}" \
    --batch 1000000000 \
    --tmp ./mobmess_tmp


