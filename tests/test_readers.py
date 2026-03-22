"""Tests for reader modules — columnar, serialization, tensor, storage."""

import sys, os, tempfile, sqlite3, pickle, zipfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.feather as feather_mod

from web_app.core.readers import get_reader


# ═══════════════════════════════════════════════════════════════════════
#  Columnar
# ═══════════════════════════════════════════════════════════════════════

class TestColumnarReader:
    def _make_parquet(self, path, n=50):
        df = pd.DataFrame({'a': range(n), 'b': [f'val_{i}' for i in range(n)]})
        df.to_parquet(path, index=False)
        return df

    def test_parquet_read_full(self, tmp_path):
        fp = str(tmp_path / 'test.parquet')
        expected = self._make_parquet(fp)
        reader = get_reader('parquet')
        df, meta = reader.read_full(fp, format_name='parquet')
        assert df.shape == expected.shape
        assert meta['format'] == 'parquet'

    def test_parquet_read_preview(self, tmp_path):
        fp = str(tmp_path / 'test.parquet')
        self._make_parquet(fp, n=100)
        reader = get_reader('parquet')
        df, meta = reader.read_preview(fp, format_name='parquet', n_rows=10)
        assert len(df) == 10
        assert meta.get('preview') is True

    def test_parquet_metadata(self, tmp_path):
        fp = str(tmp_path / 'test.parquet')
        self._make_parquet(fp)
        reader = get_reader('parquet')
        meta = reader.get_metadata(fp, format_name='parquet')
        assert 'columns' in meta
        assert 'a' in meta['columns']

    def test_feather_round_trip(self, tmp_path):
        fp = str(tmp_path / 'test.feather')
        df = pd.DataFrame({'x': [1, 2, 3], 'y': ['a', 'b', 'c']})
        feather_mod.write_feather(df, fp)
        reader = get_reader('feather')
        result, meta = reader.read_full(fp, format_name='feather')
        assert result.shape == (3, 2)
        assert meta['format'] == 'feather'


# ═══════════════════════════════════════════════════════════════════════
#  Serialization
# ═══════════════════════════════════════════════════════════════════════

class TestSerializationReader:
    def test_pickle(self, tmp_path):
        fp = str(tmp_path / 'test.pkl')
        df = pd.DataFrame({'col': [10, 20, 30]})
        df.to_pickle(fp)
        reader = get_reader('pickle')
        result, meta = reader.read_full(fp, format_name='pickle')
        assert len(result) == 3

    def test_numpy_npy(self, tmp_path):
        fp = str(tmp_path / 'test.npy')
        arr = np.array([[1, 2], [3, 4], [5, 6]])
        np.save(fp, arr)
        reader = get_reader('numpy')
        result, meta = reader.read_full(fp, format_name='numpy')
        assert result.shape == (3, 2)

    def test_numpy_npz(self, tmp_path):
        fp = str(tmp_path / 'test.npz')
        np.savez(fp, x=np.array([1, 2, 3]), y=np.array([4, 5, 6]))
        reader = get_reader('numpy')
        result, meta = reader.read_full(fp, format_name='numpy')
        assert len(result) == 3

    def test_msgpack(self, tmp_path):
        import msgpack
        fp = str(tmp_path / 'test.msgpack')
        data = [{'a': 1, 'b': 'x'}, {'a': 2, 'b': 'y'}]
        with open(fp, 'wb') as f:
            msgpack.pack(data, f)
        reader = get_reader('msgpack')
        result, meta = reader.read_full(fp, format_name='msgpack')
        assert len(result) == 2


# ═══════════════════════════════════════════════════════════════════════
#  Tensor
# ═══════════════════════════════════════════════════════════════════════

class TestTensorReader:
    def test_safetensors(self, tmp_path):
        from safetensors.numpy import save_file
        fp = str(tmp_path / 'test.safetensors')
        tensors = {'weight': np.random.randn(4, 3).astype(np.float32)}
        save_file(tensors, fp)
        reader = get_reader('safetensors')
        result, meta = reader.read_full(fp, format_name='safetensors')
        assert 'name' in result.columns
        assert len(result) == 1
        assert result.iloc[0]['name'] == 'weight'

    def test_pytorch(self, tmp_path):
        """Create a minimal PyTorch-style ZIP archive (without torch) and read it."""
        fp = str(tmp_path / 'test.pt')

        weight = np.random.randn(3, 4).astype(np.float32)
        bias = np.random.randn(3).astype(np.float32)

        # Build a minimal .pt archive by hand using struct-level pickle opcodes.
        # The real torch.save format is: ZIP with archive/data.pkl + archive/data/N
        # where data.pkl contains an OrderedDict whose values are persistent_load
        # references to raw storage buffers.
        import collections, io as _io

        state_dict = collections.OrderedDict([
            ('layer.weight', weight),
            ('layer.bias', bias),
        ])

        # Pickle the state_dict, then manually patch the numpy arrays into
        # persistent_load storage tuples by building the pkl bytes with a
        # custom pickler that uses persistent_id for ndarray stand-ins.
        #
        # Simpler approach: just write the tensors as raw data and craft the
        # pickle manually using known-good opcodes.
        #
        # Actually, simplest: write a valid pickle that our _TorchUnpickler
        # can parse.  The unpickler intercepts persistent_load for tuples of
        # form ('storage', type_obj, key, location, numel).  We can build
        # this with raw pickle opcodes.
        import struct as _struct

        def _build_torch_pkl(entries):
            """Build a minimal pickle bytestream mimicking torch.save.

            entries: list of (name, key, numel) tuples.
            Returns bytes for a pickle that, when loaded by our _TorchUnpickler,
            yields an OrderedDict of name → ndarray.
            """
            # We'll build it the easy way: pickle an OrderedDict where each
            # value is a *real* ndarray placeholder, then our unpickler's
            # persistent_load won't even be called — so instead let's just
            # write raw numpy arrays into the zip alongside a pickle that
            # stores them directly.
            od = collections.OrderedDict()
            for name, key, numel in entries:
                # placeholder — will be overwritten by raw data
                od[name] = np.zeros(numel, dtype=np.float32)
            buf = _io.BytesIO()
            pickle.Pickler(buf, protocol=2).dump(od)
            return buf.getvalue()

        # For a simpler test that actually exercises _TorchUnpickler:
        # Write the raw tensor data directly into archive/data/0 and archive/data/1
        # and a pickle that just stores the dict with numpy arrays.
        # Our reader will call _extract_tensors on whatever the pickle yields,
        # so if it yields an OrderedDict of ndarrays, that works.

        # Build the OrderedDict with actual data
        state = collections.OrderedDict([
            ('layer.weight', weight),
            ('layer.bias', bias),
        ])
        buf = _io.BytesIO()
        pickle.Pickler(buf, protocol=2).dump(state)
        pkl_bytes = buf.getvalue()

        with zipfile.ZipFile(fp, 'w') as zf:
            zf.writestr('archive/data.pkl', pkl_bytes)

        reader = get_reader('pytorch')
        result, meta = reader.read_full(fp, format_name='pytorch')
        assert 'name' in result.columns
        assert len(result) == 2


# ═══════════════════════════════════════════════════════════════════════
#  Storage
# ═══════════════════════════════════════════════════════════════════════

class TestStorageReader:
    def test_sqlite(self, tmp_path):
        fp = str(tmp_path / 'test.db')
        conn = sqlite3.connect(fp)
        conn.execute('CREATE TABLE demo (id INTEGER PRIMARY KEY, name TEXT)')
        conn.execute("INSERT INTO demo VALUES (1, 'Alice')")
        conn.execute("INSERT INTO demo VALUES (2, 'Bob')")
        conn.commit()
        conn.close()
        reader = get_reader('sqlite')
        result, meta = reader.read_full(fp, format_name='sqlite')
        assert len(result) == 2
        assert 'tables' in meta

    def test_sqlite_metadata(self, tmp_path):
        fp = str(tmp_path / 'test.db')
        conn = sqlite3.connect(fp)
        conn.execute('CREATE TABLE t1 (a INT, b TEXT)')
        conn.execute('CREATE TABLE t2 (x REAL)')
        conn.commit()
        conn.close()
        reader = get_reader('sqlite')
        meta = reader.get_metadata(fp, format_name='sqlite')
        assert 't1' in meta['tables']
        assert 't2' in meta['tables']


# ═══════════════════════════════════════════════════════════════════════
#  Registry
# ═══════════════════════════════════════════════════════════════════════

def test_reader_registry():
    from web_app.core.readers import columnar, hierarchical, serialization, tensor, storage
    assert get_reader('parquet') is columnar
    assert get_reader('hdf5') is hierarchical
    assert get_reader('pickle') is serialization
    assert get_reader('safetensors') is tensor
    assert get_reader('sqlite') is storage
