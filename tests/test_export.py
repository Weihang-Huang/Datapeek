"""Tests for the exporter module."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import numpy as np
from web_app.core.exporter import export_dataframe, export_to_csv_string, export_selection


def _sample_df():
    return pd.DataFrame({'x': [1, 2, 3], 'y': ['a', 'b', 'c']})


def test_csv_export():
    df = _sample_df()
    buf, ext, mime = export_dataframe(df, 'csv')
    content = buf.read().decode('utf-8')
    assert 'x,y' in content
    assert ext == '.csv'


def test_json_export():
    df = _sample_df()
    buf, ext, mime = export_dataframe(df, 'json')
    import json
    data = json.loads(buf.read())
    assert len(data) == 3
    assert ext == '.json'


def test_parquet_round_trip():
    df = _sample_df()
    buf, ext, mime = export_dataframe(df, 'parquet')
    result = pd.read_parquet(buf)
    assert list(result.columns) == ['x', 'y']
    assert len(result) == 3


def test_feather_round_trip():
    df = _sample_df()
    buf, ext, mime = export_dataframe(df, 'feather')
    import pyarrow.feather as f
    result = f.read_feather(buf)
    assert len(result) == 3


def test_xlsx_export():
    df = _sample_df()
    buf, ext, mime = export_dataframe(df, 'xlsx')
    assert ext == '.xlsx'
    assert buf.getbuffer().nbytes > 0


def test_npy_export():
    df = _sample_df()
    buf, ext, mime = export_dataframe(df, 'npy')
    assert ext == '.npy'


def test_pickle_export():
    df = _sample_df()
    buf, ext, mime = export_dataframe(df, 'pickle')
    result = pd.read_pickle(buf)
    assert len(result) == 3


def test_csv_string():
    df = _sample_df()
    text = export_to_csv_string(df)
    assert 'x\ty' in text


def test_selection_export():
    df = pd.DataFrame({'a': range(10), 'b': range(10, 20), 'c': range(20, 30)})
    buf, ext, mime = export_selection(df, 2, 5, 0, 2, 'csv')
    content = buf.read().decode('utf-8')
    lines = content.strip().split('\n')
    assert len(lines) == 4  # header + 3 data rows
