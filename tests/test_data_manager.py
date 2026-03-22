"""Tests for DataManager."""

import sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
from web_app.core.data_manager import DataManager


def _make_parquet(path, n=50):
    df = pd.DataFrame({'a': range(n), 'b': [f'val_{i}' for i in range(n)]})
    df.to_parquet(path, index=False)
    return df


class TestDataManager:
    def setup_method(self):
        self.dm = DataManager()
        self.tmp = tempfile.NamedTemporaryFile(suffix='.parquet', delete=False)
        self.tmp.close()
        _make_parquet(self.tmp.name, n=50)
        self.sid = 'test-session'

    def teardown_method(self):
        os.unlink(self.tmp.name)

    def _load(self):
        self.dm.load_file(self.sid, self.tmp.name, 'test.parquet', 'parquet', mode='full')

    def test_load_and_page(self):
        self._load()
        page = self.dm.get_page(self.sid, 1, 10)
        assert page['total'] == 50
        assert len(page['rows']) == 10
        assert page['page'] == 1

    def test_search(self):
        self._load()
        results = self.dm.search(self.sid, 'val_5')
        assert len(results) >= 1

    def test_sort(self):
        self._load()
        self.dm.sort(self.sid, 'a', ascending=False)
        page = self.dm.get_page(self.sid, 1, 5)
        assert page['rows'][0][0] == 49

    def test_edit_cell(self):
        self._load()
        self.dm.edit_cell(self.sid, 0, 'b', 'CHANGED')
        page = self.dm.get_page(self.sid, 1, 5)
        assert page['rows'][0][1] == 'CHANGED'

    def test_add_row(self):
        self._load()
        self.dm.add_row(self.sid, 0)
        page = self.dm.get_page(self.sid, 1, 100)
        assert page['total'] == 51

    def test_add_column(self):
        self._load()
        self.dm.add_column(self.sid, 'new_col', position=1, default='X')
        meta = self.dm.get_metadata(self.sid)
        assert 'new_col' in meta['columns']

    def test_delete_rows(self):
        self._load()
        self.dm.delete_rows(self.sid, [0, 1, 2])
        page = self.dm.get_page(self.sid, 1, 100)
        assert page['total'] == 47

    def test_delete_columns(self):
        self._load()
        self.dm.delete_columns(self.sid, ['b'])
        meta = self.dm.get_metadata(self.sid)
        assert 'b' not in meta['columns']

    def test_get_selection(self):
        self._load()
        sel = self.dm.get_selection(self.sid, 0, 5, 0, 1)
        assert sel.shape == (5, 1)

    def test_purge(self):
        self._load()
        self.dm.purge(self.sid)
        assert not self.dm.has_session(self.sid)

    def test_load_purges_previous(self):
        self._load()
        self.dm.edit_cell(self.sid, 0, 'b', 'OLD')
        # Re-load purges previous
        self.dm.load_file(self.sid, self.tmp.name, 'test.parquet', 'parquet', mode='full')
        page = self.dm.get_page(self.sid, 1, 5)
        assert page['rows'][0][1] != 'OLD'
