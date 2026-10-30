#!/bin/bash
set -euo pipefail

# Run mobmess systems using MUMmer4 --batch mode
# --batch 1000000000 (1GB chunks) prevents single-threaded suffix array sorting
# from hitting worst-case O(N^2) memory/sorting traps on large plasmid FASTA files.
mobmess systems \
    --sequences "$HOME/01_mobmess/all_plasx_clean.fasta" \
    --complete "$HOME/01_mobmess/all_plasx_circular.txt" \
    --output ./all_plasx-mobmess \
    --threads "${THREADS:-32}" \
    --batch 1000000000 \
    --tmp ./mobmess_tmp


