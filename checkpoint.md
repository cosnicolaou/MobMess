# Checkpoint and Resume Design for MobMess & MUMmer4

This document outlines the checkpointing architecture for long-running `mobmess systems` executions, detailing how each computational phase can be made resilient to timeouts, crashes, and resource limits.

---

## Overview of the Computation Pipeline

A full run of `mobmess systems` consists of the following phases:

```
[Phase 1] Suffix Array Construction (nucmer)
    │     Single-threaded, in-memory index construction of reference database.
    ▼
[Phase 2] Multi-Threaded Query Alignment (nucmer)
    │     Multi-threaded OpenMP query streaming against suffix array index.
    ▼
[Phase 3] Delta Filtering (mummer_fast_deltafilter)
    │     1-to-1 alignment filtering across all candidate alignment blocks.
    ▼
[Phase 4] Pairwise ANI & Coverage Calculation (get_mummer_query_coverage_py)
    │     Extract coverage, ANI, and global identities into `{output}_ani.txt`.
    ▼
[Phase 5] Graph Partitioning & System Inference (derep_sources)
          Connected components, backbone identification, and `.graphml` export.
```

---

## Detailed Checkpointing Strategy by Phase

### Phase 1: Reference Indexing (Suffix Array Construction)
* **Status**: **Implemented** via `--save-sa` and `--load-sa`.
* **Mechanism**:
  - `nucmer` builds the 48-bit suffix array in memory.
  - With `--save-sa <prefix>`, MUMmer4 flushes the binary index files (`.sa`, `.isa`, `.aux`, `.lcp`, `.kmer`) to disk immediately after index construction finishes (before query matching begins).
  - Subsequent runs with `--load-sa <prefix>` bypass Phase 1 entirely, memory-mapping the pre-built index in ~5 seconds.

---

### Phase 2: Multi-Threaded Query Alignment (`nucmer`)
* **Problem**:
  - `nucmer` has no internal resume capability. If a job times out during Phase 2, `nucmer` would restart from query sequence #1.
* **Checkpoint Architecture (Query Chunking)**:
  1. **Query Partitioning**:
     - The query FASTA is split into $N$ chunk files (`chunk_001.fa`, `chunk_002.fa`, ..., `chunk_N.fa`) of roughly 100 MB or ~4,000 plasmids each.
  2. **Per-Chunk Checkpoint Loop**:
     - For each chunk $i \in [1, N]$:
       - Check if `chunk_i.delta` and `chunk_i.done` exist.
       - **If yes**: Skip immediately (already finished).
       - **If no**: Run:
         ```bash
         nucmer --load-sa <sa_prefix> -p ./chunks/chunk_i -t <threads> ref.fa ./chunks/chunk_i.fa
         touch ./chunks/chunk_i.done
         ```
  3. **Resumption**:
     - If interrupted at chunk 37 of 50, re-running the command inspects the filesystem, skips chunks 1–36 in under a second, and resumes at chunk 37.
  4. **Merge**:
     - Once all chunks have a `.done` sentinel, concatenate the chunk `.delta` files:
       ```
       <header from chunk_001.delta>
       <all alignment records from chunk_001.delta through chunk_N.delta>
       ```
     - Write to `mummer_align.delta`.

---

### Phase 3: Post-Alignment Delta Filtering (`mummer_fast_deltafilter`)
* **Current Behavior**:
  - `mummer_fast_deltafilter` takes ~1 hr 45 min across all cores on full plasmid datasets.
  - Currently, it splits alignment blocks into $T$ coarse thread chunks (e.g. 32 chunks for 32 threads) and spawns an ephemeral bash script for each that appends (`>>`) to `{chunk_i}_filter` inside an ephemeral temp directory.
  - **Vulnerability**: If the node crashes or times out 1 hour and 40 minutes in, the temporary directory is lost, and the entire 1.75 hours of compute is wasted because there is zero progress tracking or recovery.

* **Worker/Unit-of-Work Level Checkpoint Architecture**:
  1. **Granular Unit of Work**:
     - Partition the alignment blocks into $M$ granular work units (e.g. batches of 100–500 sequence pairs, yielding hundreds or thousands of discrete tasks).
  2. **Atomic Worker Checkpointing**:
     - Checkpoint directory: `<tmp_or_checkpoint_dir>/delta_filter_tasks/`.
     - For unit of work $k$:
       - A worker thread/process checks if `<task_dir>/task_{k}.filtered.delta` already exists and is non-empty.
       - If it exists, the worker immediately **skips** it (0 overhead).
       - If not, the worker executes `delta-filter -q -r` for its assigned block batch, writes to a temporary file `<task_dir>/task_{k}.tmp`, and performs an **atomic filesystem rename** (`os.replace`) to `<task_dir>/task_{k}.filtered.delta`.
  3. **Fault Tolerance ("Only Current In-Flight Unit Lost")**:
     - If the system dies mid-run:
       - All previously completed units ($k < K$) remain fully intact on disk.
       - Only the specific units currently in-flight across the active worker threads at the exact moment of failure are interrupted.
       - Atomic rename ensures no partially-written/corrupt delta files can ever be mistaken for valid checkpoints.
     - Upon restart, the coordinator scans `<task_dir>/`, recognizes all completed tasks, and only dispatches the remaining uncompleted units to the worker pool.
  4. **Parallel Execution via Thread/Process Pool**:
     - Uses Python's `concurrent.futures.ProcessPoolExecutor` or `ThreadPoolExecutor(max_workers=n_jobs)` feeding from a work queue.
     - Dynamic work stealing prevents straggler worker threads from holding up the pipeline.
  5. **Final Concatenation**:
     - When all units $1..M$ are confirmed present, streams and concatenates the individual `task_{k}.filtered.delta` files into the single `mummer_align.qr_filter` delta file.

---

### Phase 4: Alignment Parsing & ANI Table Generation
* **Current Behavior**:
  - `read_mummer_aln_blocks` parses the filtered delta file into DataFrame records (~9 min).
  - `get_mummer_query_coverage_py` calculates ANI and query coverage, writing `<output>_ani.txt` and `<output>_ani_blocks.txt`.
* **Worker-Level Checkpointing**:
  - `aln_blocks` dataframe is pickled to `<tmp>/mummer_align.qr_filter.pkl.blp`. If this file exists, parsing is skipped.
  - Pairwise ANI calculation can be chunked by reference sequence blocks; if `<output>_ani.txt` exists and is non-empty, the entire stage is skipped.

---

### Phase 5: Dereplication and Graph Generation
* Runs in minutes once the ANI table is available. Output files:
  - `<output>_contigs.txt`
  - `<output>_clusters.txt`
  - `<output>_systems.txt`
  - `<output>_contig_graph.graphml`
  - `<output>_cluster_graph.graphml`

---

## Implementation Plan for Query Chunking in `mobmess`

1. **New CLI Arguments in `mobmess systems`**:
   - `--chunks <int>`: Number of query chunks (or `--chunk-size <int>`: number of sequences per chunk). Default: `None` (monolithic run).
   - `--resume`: Automatically scan existing chunk outputs and resume from the first incomplete chunk.

2. **Integration in `ani_utils.py`**:
   - `run_nucmer_chunked(fasta, output, sa_prefix, n_chunks=..., threads=...)`:
     - Creates chunk FASTA files if not present.
     - Iterates chunks, skipping completed ones.
     - Concatenates `.delta` outputs upon completion.
