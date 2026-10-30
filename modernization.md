# MobMess Modernization Summary (Python 3.13)

This document summarizes the changes made to modernize **MobMess** and its companion library **PlasX** (`../PlasX`) to support modern Python versions (Python 3.10 through 3.13) and modern scientific package versions (NumPy 2.x, Pandas 3.x, SciPy 1.18+, Numba 0.68+, igraph 1.0+, and Matplotlib 3.10+).

---

## 1. Environment Setup

A dedicated Conda environment named `mobmess-py313` was configured and verified on macOS (Apple Silicon):

```bash
conda create -y -n mobmess-py313 -c conda-forge -c bioconda \
    python=3.13 numpy pandas scipy scikit-learn python-igraph numba python-blosc mummer4 pytest \
    matplotlib seaborn jinja2 pypdf
conda activate mobmess-py313
pip install -e ../PlasX
pip install -e .
```

### Installed Package Versions
* **Python**: 3.13.16
* **NumPy**: 2.5.4
* **Pandas**: 3.0.6
* **SciPy**: 1.18.1
* **Numba**: 0.68.0
* **igraph**: 1.0.0
* **python-blosc**: 1.11.4
* **MUMmer4**: 4.0.1
* **Matplotlib**: 3.10.9
* **Seaborn**: 0.13.2
* **pypdf**: 6.21.4

---

## 2. Incompatibilities Identified and Resolved

### A. NumPy 1.24+ & 2.0 Incompatibilities
* **Deprecated/Removed Dtypes**: Aliases `np.bool`, `np.int`, and `np.str` were removed in NumPy 1.24+ and cause fatal `AttributeError: module 'numpy' has no attribute 'bool'` in modern versions.
* **MobMess Fixes**:
  * `mobmess/sp_utils.py`: Replaced `assert y.dtype == np.bool` with `assert y.dtype == bool`.
  * `mobmess/ani_utils.py`: Replaced `sp.astype(np.int)`, `dtype=np.int`, and `np.empty(..., np.int)` with standard `int`.
* **PlasX Fixes**:
  * `plasx/mmseqs.py`: Replaced `np.str` with `str`, `np.bool` with `bool` or `np.bool_`.
  * `plasx/utils.py`: Replaced `x.astype(np.bool)` with `x.astype(bool)`.

### B. Pandas 2.x & 3.x Breaking Changes
* **`delim_whitespace=True` Removal**:
  * `mobmess/ani_utils.py`: `pd.read_csv(..., delim_whitespace=True)` replaced with `sep=r'\s+'`.
* **`StringArray` Extension Array Compatibility**:
  * `mobmess/graph_utils.py`: Pandas now stores strings in `StringArray`, which does not have `.flatten()`. Changed `vertex_attrs[c].values.flatten()` to `np.asarray(vertex_attrs[c]).flatten()`.
* **`Categorical` Comparison `TypeError`**:
  * `mobmess/ani_utils.py`: Element-wise comparison between two categorical series with differing categories (`similarities['query'] != similarities['reference']`) now raises `TypeError`. Replaced with array-level comparison: `similarities['query'].to_numpy() != similarities['reference'].to_numpy()`.
* **`DataFrame.append()` Removal**:
  * `mobmess/ani_utils.py`: Replaced `vertex_attrs.append(...)` with `pd.concat([vertex_attrs, ...])`.
* **`pd.concat` Positional Arguments**:
  * `mobmess/plot.py`: Positional axis arguments like `pd.concat([...], 1)` were made keyword-only in Pandas 2.0. Replaced with `axis=1`.
* **`inplace=True` and `.cat.categories` Deprecations**:
  * `mobmess/ani_utils.py`: Replaced direct assignment `similarities['col'].cat.categories = [...]` with `.cat.rename_categories(...)`.
  * `mobmess/ani_utils.py` & `mobmess/plot.py`: Replaced `drop(..., inplace=True)`, `fillna(..., inplace=True)`, and `set_index(..., inplace=True)` with explicit re-assignment.
* **`groupby().apply()` Group Key Exclusion**:
  * `mobmess/plot.py`: In Pandas 2.2+/3.0, `include_groups=False` is enforced, removing the grouping column from the data frame passed into `apply()`. Refactored `interval_merge_self` to iterate over groups explicitly (`for _, group in functions.groupby(...)`).
* **`is_categorical_dtype` Deprecation**:
  * `plasx/pd_utils.py`: Replaced deprecated `pd.api.types.is_categorical_dtype()` with `isinstance(s.dtype, pd.CategoricalDtype)`.

### C. SciPy Sparse Matrix Modernization (SparseEfficiencyWarning)
* **Diagonal Assignment (`setdiag`)**:
  * `mobmess/utils.py`: Previously assigned `X[i, i] = values` via 2D fancy indexing on a `csr_matrix`, which triggers `SparseEfficiencyWarning: Changing the sparsity structure of a csr_matrix is expensive. lil and dok are more efficient.`
  * Replaced with SciPy's native `X.setdiag(values)` followed by `X.eliminate_zeros()`, which updates diagonals directly without sparsity structure modification warnings.
* **Inverted Sparse Masking (`sp_mask`)**:
  * `mobmess/sp_utils.py`: Previously used `new_x[i, j] = 0` on CSR matrices when `invert=True`, triggering `SparseEfficiencyWarning` when indexing previously unstored cells.
  * Replaced with coordinate-level filtering (`COO` representation), preserving `np.inf` values and avoiding in-place sparsity mutations.

### D. Visualization & Matplotlib / PDF Modernization
* **Matplotlib `grid(b=False)` Removal**:
  * `mobmess/plot.py`: Replaced `ax.grid(b=False, ...)` with `ax.grid(visible=False, ...)`.
  * `mobmess/plot.py`: Added explicit `ax2.set_xticks(xticks)` before `ax2.set_xticklabels(...)` to silence FixedLocator warnings.
* **Pandas Styler Modernization**:
  * `mobmess/plot.py`: Added `'selector': 'table'` to `set_table_styles()`, used `hide(axis='index')` instead of `hide_index()`, and used `to_html()` instead of `render()`.
* **`PyPDF2` → `pypdf` & wkhtmltopdf Fallback**:
  * `mobmess/plot.py`: Added support for `pypdf` (`PdfMerger`), falling back to `PyPDF2`.
  * Added a graceful fallback: on platforms where `wkhtmltopdf` is unavailable (e.g., Apple Silicon where it is unmaintained and lacks official builds), `visualize` saves the sequence alignment plot to the output PDF and writes the gene annotations table to `{output}_annotations.html` rather than failing.

### E. Packaging & Infrastructure
* **`pyproject.toml`**: Added standard PEP 517/621 configuration for both `MobMess` and `PlasX`.
* **`setup.py` & `requirements.txt`**:
  * Updated `python_requires` to `>=3.10`.
  * Added classifiers for Python 3.10, 3.11, 3.12, and 3.13.
  * Replaced `python-igraph` with `igraph`.
  * Added optional extras: `visualize` (`matplotlib`, `seaborn`, `pypdf`, `jinja2`) and `test` (`pytest`).
* **Git Configuration**: Added `.gitignore` to both repositories to prevent caching/build artifacts from being tracked.
* **Automated Tests**: Added `test/test_mobmess.py` providing unit and end-to-end regression tests.

---

## 3. Verification Results

### Pytest Test Suite
```bash
$ conda run -n mobmess-py313 pytest test/test_mobmess.py -v
============================= test session starts ==============================
platform darwin -- Python 3.13.16, pytest-9.1.1, pluggy-1.7.0
rootdir: /Users/cnicolaou/LocalOnly/dev/github.com/cosnicolaou/MobMess
configfile: pyproject.toml
collected 8 items

test/test_mobmess.py::test_imports PASSED                                [ 12%]
test/test_mobmess.py::test_sp_utils PASSED                               [ 25%]
test/test_mobmess.py::test_graph_utils PASSED                            [ 37%]
test/test_mobmess.py::test_pd_sparse_pivot PASSED                        [ 50%]
test/test_mobmess.py::test_nb_utils PASSED                               [ 62%]
test/test_mobmess.py::test_cli_help PASSED                               [ 75%]
test/test_mobmess.py::test_infer_systems_from_precomputed_ani PASSED     [ 87%]
test/test_mobmess.py::test_visualize PASSED                              [100%]

============================== 8 passed in 2.02s ===============================
```

### CLI Verification
* **`mobmess systems`**:
  Successfully aligns, filters, and generates contig/cluster/system tables and `.graphml` files from `test/test-contigs.fa`.
* **`mobmess visualize`**:
  Successfully parses alignment blocks, calculates Jaccard linkages, aligns loci, centers on anchors, and writes output PDF.
