import os
import pathlib
import tempfile
import pytest
import numpy as np
import pandas as pd
import scipy.sparse

from mobmess import utils, ani_utils, graph_utils, pd_utils, sp_utils, nb_utils, plot

TEST_DIR = pathlib.Path(__file__).parent.resolve()


def test_imports():
    assert utils is not None
    assert ani_utils is not None
    assert graph_utils is not None
    assert pd_utils is not None
    assert sp_utils is not None
    assert nb_utils is not None
    assert plot is not None


def test_sp_utils():
    # Test as_flat
    m = scipy.sparse.csr_matrix([[1, 0], [0, 2]])
    assert list(sp_utils.as_flat(m.data)) == [1, 2]

    # Test copy_sp
    copied = sp_utils.copy_sp(m)
    assert (copied.toarray() == m.toarray()).all()

    # Test sp_mask
    mask = scipy.sparse.csr_matrix([[True, False], [False, True]])
    masked = sp_utils.sp_mask(m, y=mask)
    assert (masked.toarray() == m.toarray()).all()


def test_graph_utils():
    adj = scipy.sparse.csr_matrix([[0, 1], [0, 0]])
    g = graph_utils.create_ig(adj, rownames=['A', 'B'], colnames=['A', 'B'])
    assert g.vcount() == 2
    assert g.ecount() == 1
    assert g.vs['name'] == ['A', 'B']

    v_df, e_df = graph_utils.ig_to_df(g)
    assert len(v_df) == 2
    assert len(e_df) == 1

    reach = graph_utils.reachability(adj)
    assert reach.shape == (2, 2)


def test_pd_sparse_pivot():
    df = pd.DataFrame({
        'query': ['c1', 'c2', 'c1'],
        'reference': ['c1', 'c2', 'c2'],
        'weight': [1.0, 1.0, 0.8]
    })
    g = pd_utils.sparse_pivot(df, index='query', columns='reference', values='weight', square=True, rettype='ig')
    assert g.vcount() == 2
    assert g.ecount() == 3


def test_nb_utils():
    pos = np.array([0, 10, 20], dtype=np.int64)
    data = np.array([2, -1, -1], dtype=np.int32)
    cov = nb_utils.cov_to_dense(pos, data, 25)
    assert len(cov) == 25
    assert cov[0] == 2
    assert cov[9] == 2
    assert cov[10] == 1


def test_cli_help(capsys):
    from mobmess import mobmess_script
    parser = mobmess_script.get_parser()
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(['-h'])
    assert exc_info.value.code == 0


def test_infer_systems_from_precomputed_ani():
    from mobmess.mobmess_script import get_parser
    parser = get_parser()

    with tempfile.TemporaryDirectory() as tmpdir:
        out_prefix = os.path.join(tmpdir, 'test_out')
        fa_file = str(TEST_DIR / 'test-contigs.fa')
        circ_file = str(TEST_DIR / 'test-contigs-circular.txt')
        ani_file = str(TEST_DIR / 'test-contigs-mobmess_ani.txt')

        args = parser.parse_args([
            'systems',
            '-s', fa_file,
            '-c', circ_file,
            '-a', ani_file,
            '-o', out_prefix,
        ])
        args.func(args)

        assert os.path.exists(out_prefix + '_contigs.txt')
        assert os.path.exists(out_prefix + '_clusters.txt')
        assert os.path.exists(out_prefix + '_systems.txt')
        assert os.path.exists(out_prefix + '_contig_graph.graphml')
        assert os.path.exists(out_prefix + '_cluster_graph.graphml')

        contigs_df = pd.read_csv(out_prefix + '_contigs.txt', sep='\t')
        assert len(contigs_df) == 123
        clusters_df = pd.read_csv(out_prefix + '_clusters.txt', sep='\t')
        assert len(clusters_df) == 123
        systems_df = pd.read_csv(out_prefix + '_systems.txt', sep='\t')
        assert len(systems_df) == 4


def test_visualize():
    from mobmess.mobmess_script import get_parser
    parser = get_parser()

    with tempfile.TemporaryDirectory() as tmpdir:
        out_pdf = os.path.join(tmpdir, 'fig.pdf')
        fa_file = str(TEST_DIR / 'test-contigs.fa')
        anno_file = str(TEST_DIR / 'test-contigs-annotations.txt')
        aln_file = str(TEST_DIR / 'test-contigs-mobmess_ani_blocks.txt')

        args = parser.parse_args([
            'visualize',
            '-s', fa_file,
            '-a', anno_file,
            '--contigs', 'CHI0047_000000002374,CHI0169_000000002212',
            '--align', aln_file,
            '-o', out_pdf,
        ])
        args.func(args)

        assert os.path.exists(out_pdf)


def test_systems_batch():
    from mobmess.mobmess_script import get_parser
    from mobmess import ani_utils
    parser = get_parser()

    # Verify parser accepts --batch and --minmatch
    args = parser.parse_args([
        'systems',
        '-s', 'seqs.fa',
        '-c', 'circ.txt',
        '-o', 'out',
        '--batch', '500000000',
        '--minmatch', '20',
    ])
    assert args.batch == 500000000
    assert args.minmatch == 20

    # Functional test of batch mode with nucmer
    with tempfile.TemporaryDirectory() as tmpdir:
        fa_file = str(TEST_DIR / 'test-contigs.fa')
        out1 = os.path.join(tmpdir, 'out_nobatch')
        out2 = os.path.join(tmpdir, 'out_batch')

        # 1. Run nucmer without batch
        ani_utils.run_nucmer(fa_file, out1, threads=2)
        assert os.path.exists(out1 + '.delta')

        # 2. Run nucmer with small batch (e.g. 200,000 bases to force multi-batch chunks)
        ani_utils.run_nucmer(fa_file, out2, threads=2, batch=200000)
        assert os.path.exists(out2 + '.delta')

        size1 = os.path.getsize(out1 + '.delta')
        size2 = os.path.getsize(out2 + '.delta')
        assert size1 > 1000 and size2 > 1000
        # Both should produce comparable alignment volume (within 5%)
        assert abs(size1 - size2) / size1 < 0.05
