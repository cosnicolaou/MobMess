# Discrepancies Investigation: Test Outputs vs Paper Reference Data

This document investigates and explains why `mobmess systems` outputs differ from the paper's committed reference files in `test/`, specifically comparing:
- `test-contigs-mobmess_ani.txt`
- `test-contigs-mobmess_clusters.txt`
- `test-contigs-mobmess_contigs.txt`
- `test-contigs-mobmess_systems.txt`

---

## 1. Summary of Findings

| Output File | Using Precomputed `--ani` | Running Live `nucmer` (MUMmer 4) | Root Cause |
|---|---|---|---|
| `_contigs.txt` | **Exact Match** (123 / 123 rows) | Slight cluster differences | Exact match when using paper's ANI |
| `_clusters.txt` | **Exact Match** (123 / 123 rows) | Slight cluster differences | Exact match when using paper's ANI |
| `_systems.txt` | **Content matches, counts differ** | Content matches, counts differ | Upstream author bug fix in git commit `1bbdd1a1` (deduplication) was never refreshed in reference file |
| `_ani.txt` | N/A (Input file) | **10,903 pairs vs 15,129 pairs** | MUMmer 3.23 (suffix trees) vs MUMmer 4.0.1 (suffix arrays) chaining/clustering thresholds |

---

## 2. Discrepancy in `_systems.txt`: The Upstream Deduplication Bug Fix

When running `mobmess systems` with the paper's precomputed ANI table (`-a test/test-contigs-mobmess_ani.txt`):
- All 4 plasmid systems (`PS1`, `PS2`, `PS3`, `PS4`), their backbone cluster IDs (`0`, `1`, `4`, `9`), and compound plasmids match the paper.
- However, comparing the values in `number_of_backbone_plasmids` and `backbone_plasmids`:

| System | New Count | Committed `_systems.txt` Count | Observation |
|---|---|---|---|
| **PS1** | 1 | 1 | Exact match |
| **PS2** | **73** | **146** | In reference file, each plasmid name appears **twice** (`AST0016...\|AST0016...`) |
| **PS3** | **2** | **6** | In reference file, each plasmid name appears **three times** |
| **PS4** | **20** | **60** | In reference file, each plasmid name appears **three times** |

### Git History Root Cause:
In commit `1bbdd1a1d73adb6656479fbb0eb3591d91f19c50` (*"Fixed redundancy issue in format_derep_output()"*), the original author (Michael Yu) explicitly fixed a bug in `mobmess/ani_utils.py:format_systems()`:

```python
# Before commit 1bbdd1a1:
backbone_2_backbone_plasmid = backbone_tmp.groupby('cluster')['contig'].apply(sorted)...

# After commit 1bbdd1a1 (Author's fix):
backbone_2_backbone_plasmid = backbone_tmp.drop_duplicates(['cluster','contig']).groupby('cluster')['contig'].apply(sorted)...
```

Because `backbone_tmp` was created from an un-deduplicated `explode('backbone')` join, contigs belonging to multi-backbone systems were replicated multiple times. 

**The author committed the code fix to deduplicate plasmids, but forgot to regenerate and commit the updated reference file `test/test-contigs-mobmess_systems.txt`.** Therefore, the modernized code correctly outputs the deduplicated counts (73 unique plasmids for PS2 instead of 146 duplicated names).

---

## 3. Discrepancy in `_ani.txt`: MUMmer 3 vs MUMmer 4 Algorithmic Divergence

When running `mobmess systems` from scratch without the precomputed `--ani` flag:
- The reference file `test-contigs-mobmess_ani.txt` contains exactly **15,129 rows**. Because the FASTA has 123 contigs, this represents a complete dense Cartesian product ($123 \times 123 = 15,129$).
- Live execution using the modern `mummer4` package produces **10,903 rows**.

### Root Cause:
1. **Engine Transition from MUMmer 3 to MUMmer 4**:
   - The paper's reference data was generated using **MUMmer 3.23** (which used suffix trees).
   - Modern environments and Bioconda run **MUMmer 4.0.1** (which replaced suffix trees with a 48-bit `libdivsufsort` suffix array).
2. **Clustering & Extension Differences (`mgaps`)**:
   - In MUMmer 4, the heuristic match clustering (`mgaps`) and extension algorithms differ slightly from MUMmer 3.
   - For distant, low-homology plasmid pairs where exact matches fail to cluster into a region $\ge \text{mincluster}$ (default 65 bp), MUMmer 4 discards the alignment block and outputs no delta record.
   - MUMmer 3 reported marginal alignment blocks for these pairs, resulting in 15,129 pairs in the reference table.
3. **Identical Math on Overlapping Blocks**:
   - When fed the same alignment blocks (`test-contigs-mobmess_ani_blocks.txt`), the modernized `get_mummer_query_coverage_py()` reproduces the reference ANI table down to machine floating-point precision ($\Delta < 1.11 \times 10^{-16}$). The numerical logic is identical; the difference is purely which alignment pairs were emitted upstream by `nucmer`.

---

## 4. Discrepancy in `_contigs.txt` and `_clusters.txt`: Row Counts and 1-to-1 Mapping

- Both `_contigs.txt` and `_clusters.txt` have **123 rows** (corresponding to the 123 input contigs in `test-contigs.fa`).
- When using `--ani test-contigs-mobmess_ani.txt`:
  - `_contigs.txt`: **Exact 100% byte-for-byte match**.
  - `_clusters.txt`: **Exact 100% byte-for-byte match**.
- A previous unit test failure was due to an outdated assertion expecting `120` rows, whereas the dataset has always contained 123 sequences (`grep -c "^>" test/test-contigs.fa` returns 123).

---

## 5. Conclusions & Recommendations

1. **For exact reproduction of published paper results**:
   - Always supply `--ani test/test-contigs-mobmess_ani.txt` (or Zenodo record 5819401 for the full dataset).
2. **For reference files in version control**:
   - The committed `test/test-contigs-mobmess_systems.txt` contains stale duplicated data from before commit `1bbdd1a1`. It should either be updated to reflect the author's deduplicated output or tested using unique set comparison.
3. **For scratch runs on novel datasets**:
   - Expect slightly sparser pairwise outputs with MUMmer 4.0.1 compared to legacy MUMmer 3.23, as MUMmer 4 omits pairs with no valid clustered anchors.
