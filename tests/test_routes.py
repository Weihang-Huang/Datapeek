"""Tests for Flask routes — upload, data, export."""

import sys, os, tempfile, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
from io import BytesIO
from web_app.app import create_app


def _make_parquet_bytes():
    df = pd.DataFrame({'a': range(20), 'b': [f'val_{i}' for i in range(20)]})
    buf = BytesIO()
    df.to_parquet(buf, index=False)
    buf.seek(0)
    return buf.read()


class TestUploadRoute:
    def setup_method(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_index(self):
        resp = self.client.get('/')
        assert resp.status_code == 200
        assert b'DataPeek' in resp.data

    def test_upload_parquet(self):
        data = _make_parquet_bytes()
        resp = self.client.post('/upload', data={
            'file': (BytesIO(data), 'test.parquet'),
        }, content_type='multipart/form-data')
        result = json.loads(resp.data)
        assert 'redirect' in result or 'prompt' in result

    def test_upload_unsupported(self):
        resp = self.client.post('/upload', data={
            'file': (BytesIO(b'hello'), 'test.txt'),
        }, content_type='multipart/form-data')
        result = json.loads(resp.data)
        assert 'error' in result


class TestDataRoute:
    def setup_method(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        # Upload a file first
        data = _make_parquet_bytes()
        self.client.post('/upload', data={
            'file': (BytesIO(data), 'test.parquet'),
        }, content_type='multipart/form-data')

    def test_view_page(self):
        resp = self.client.get('/view')
        assert resp.status_code == 200

    def test_metadata(self):
        resp = self.client.get('/metadata')
        result = json.loads(resp.data)
        assert 'columns' in result

    def test_data_page(self):
        resp = self.client.get('/data?page=1&per_page=10')
        result = json.loads(resp.data)
        assert 'rows' in result
        assert len(result['rows']) <= 10

    def test_search(self):
        resp = self.client.get('/data/search?q=val_1')
        result = json.loads(resp.data)
        assert isinstance(result, list)

    def test_sort(self):
        resp = self.client.post('/data/sort',
                                data=json.dumps({'by': 'a', 'ascending': False}),
                                content_type='application/json')
        assert resp.status_code == 200

    def test_edit(self):
        resp = self.client.post('/data/edit',
                                data=json.dumps({'row': 0, 'col': 'b', 'value': 'EDIT'}),
                                content_type='application/json')
        assert resp.status_code == 200


class TestExportRoute:
    def setup_method(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        data = _make_parquet_bytes()
        self.client.post('/upload', data={
            'file': (BytesIO(data), 'test.parquet'),
        }, content_type='multipart/form-data')

    def test_export_csv(self):
        resp = self.client.get('/export/full?fmt=csv')
        assert resp.status_code == 200
        assert b'a,b' in resp.data

    def test_export_json(self):
        resp = self.client.get('/export/full?fmt=json')
        assert resp.status_code == 200

    def test_copy(self):
        resp = self.client.post('/copy',
                                data=json.dumps({'row_start': 0, 'row_end': 3, 'col_start': 0, 'col_end': 2}),
                                content_type='application/json')
        result = json.loads(resp.data)
        assert 'csv_text' in result

    def test_reset(self):
        resp = self.client.post('/reset')
        result = json.loads(resp.data)
        assert 'redirect' in result
