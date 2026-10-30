#!/bin/bash
set -euo pipefail

# Directory of this script (MobMess root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_DIR="${SCRIPT_DIR}/test"

PREFIX="test-contigs"
THREADS="${THREADS:-4}"
OUT_DIR="${1:-${SCRIPT_DIR}/test_output}"

echo "=========================================================="
echo " Running MobMess tutorial test (per the original paper)    "
echo "=========================================================="
echo "Test data dir:  ${TEST_DIR}"
echo "Output prefix:  ${OUT_DIR}/${PREFIX}-mobmess"
echo "Threads:        ${THREADS}"
echo "=========================================================="

mkdir -p "${OUT_DIR}"

# Run mobmess systems using the precomputed pairwise alignments (as specified in the paper tutorial)
mobmess systems \
    --sequences "${TEST_DIR}/${PREFIX}.fa" \
    --complete "${TEST_DIR}/${PREFIX}-circular.txt" \
    --ani "${TEST_DIR}/${PREFIX}-mobmess_ani.txt" \
    --output "${OUT_DIR}/${PREFIX}-mobmess" \
    --threads "${THREADS}"

echo ""
echo "=== 1. Summary of Inferred Plasmid Systems ==="
cut -f1,2,3,6,7 "${OUT_DIR}/${PREFIX}-mobmess_systems.txt"

echo ""
echo "=== 2. Sample Contig Assignments (first 5 rows) ==="
head -n 6 "${OUT_DIR}/${PREFIX}-mobmess_contigs.txt"

echo ""
echo "=== 3. Comparing Generated Files Against Reference Data ==="
DIFF_FAILED=0

for SUFFIX in "_contigs.txt" "_clusters.txt"; do
    REF="${TEST_DIR}/${PREFIX}-mobmess${SUFFIX}"
    GEN="${OUT_DIR}/${PREFIX}-mobmess${SUFFIX}"
    if diff -q "${REF}" "${GEN}" >/dev/null; then
        echo "  [PASS] ${SUFFIX} matches paper reference exactly."
    else
        echo "  [FAIL] ${SUFFIX} differs from paper reference."
        DIFF_FAILED=1
    fi
done

# Note on _systems.txt:
# The paper reference file in test/ contains redundant duplicated plasmid names
# from before the author's code fix in commit 1bbdd1a1 (see descrepancies.md).
# Here we check that the 4 systems (PS1..PS4) and their backbone clusters match.
echo "  [INFO] Checking _systems.txt system definitions..."
SYSTEMS_MATCH=$(python3 -c "
import pandas as pd
ref = pd.read_csv('${TEST_DIR}/${PREFIX}-mobmess_systems.txt', sep='\t')
gen = pd.read_csv('${OUT_DIR}/${PREFIX}-mobmess_systems.txt', sep='\t')
cols = ['system_name', 'backbone_cluster', 'number_of_compound_clusters', 'number_of_compound_plasmids']
if ref[cols].equals(gen[cols]):
    print('PASS')
else:
    print('FAIL')
")

if [ "${SYSTEMS_MATCH}" = "PASS" ]; then
    echo "  [PASS] _systems.txt plasmid system definitions (PS1-PS4) match paper reference."
else
    echo "  [FAIL] _systems.txt plasmid system definitions differ."
    DIFF_FAILED=1
fi

echo "=========================================================="
if [ ${DIFF_FAILED} -eq 0 ]; then
    echo " ALL CHECKS PASSED: Output matches original paper!"
else
    echo " SOME CHECKS FAILED: Review output differences above."
fi
echo "=========================================================="
