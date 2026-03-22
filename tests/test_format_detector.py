"""Tests for format_detector.detect_format()."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from web_app.core.format_detector import detect_format


def test_parquet():
    assert detect_format('data.parquet', b'PAR1' + b'\x00' * 100) == 'parquet'


def test_feather():
    assert detect_format('data.feather', b'ARROW1' + b'\x00' * 100) == 'feather'


def test_orc():
    assert detect_format('data.orc', b'ORC' + b'\x00' * 100) == 'orc'


def test_avro():
    assert detect_format('data.avro', b'Obj\x01' + b'\x00' * 100) == 'avro'


def test_hdf5():
    assert detect_format('data.h5', b'\x89HDF\r\n\x1a\n' + b'\x00' * 100) == 'hdf5'


def test_netcdf():
    assert detect_format('data.nc', b'CDF\x01' + b'\x00' * 100) == 'netcdf'
    assert detect_format('data.nc', b'CDF\x02' + b'\x00' * 100) == 'netcdf'


def test_numpy():
    assert detect_format('data.npy', b'\x93NUMPY' + b'\x00' * 100) == 'numpy'


def test_sqlite():
    assert detect_format('data.db', b'SQLite format 3\x00' + b'\x00' * 100) == 'sqlite'


def test_pickle():
    assert detect_format('data.pkl', b'\x80\x04\x95' + b'\x00' * 100) == 'pickle'
    assert detect_format('data.pkl', b'\x80\x05\x95' + b'\x00' * 100) == 'pickle'


def test_unsupported():
    assert detect_format('readme.txt', b'Hello world') is None
    assert detect_format('data.csv', b'col1,col2') is None


def test_extension_fallback_msgpack():
    # MessagePack has no magic bytes — extension-only
    assert detect_format('data.msgpack', b'\x92\xa3foo\xa3bar') == 'msgpack'

