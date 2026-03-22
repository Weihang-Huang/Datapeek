"""Readers for serialization formats: Pickle, MessagePack, NumPy (.npy/.npz)."""

from __future__ import annotations

import io
import os
import pickle

import numpy as np
import pandas as pd
import msgpack


# ═══════════════════════════════════════════════════════════════════════
#  Pickle
# ═══════════════════════════════════════════════════════════════════════

def _to_dataframe(obj) -> pd.DataFrame:
    """Best-effort conversion of an arbitrary Python object to a DataFrame."""
    if isinstance(obj, pd.DataFrame):
        return obj
    if isinstance(obj, pd.Series):
        return obj.to_frame()
    if isinstance(obj, np.ndarray):
        if obj.ndim == 1:
            return pd.DataFrame(obj, columns=['value'])
        elif obj.ndim == 2:
            return pd.DataFrame(obj)
        else:
            return pd.DataFrame(obj.reshape(obj.shape[0], -1))
    if isinstance(obj, dict):
        # dict of lists / dict of scalars
        try:
            return pd.DataFrame(obj)
        except (ValueError, TypeError):
            return pd.DataFrame(list(obj.items()), columns=['key', 'value'])
    if isinstance(obj, (list, tuple)):
        if obj and isinstance(obj[0], dict):
            return pd.DataFrame(obj)
        return pd.DataFrame(obj, columns=['value'])
    return pd.DataFrame([{'value': str(obj)}])


def pickle_read_full(filepath: str) -> tuple[pd.DataFrame, dict]:
    with open(filepath, 'rb') as f:
        obj = pickle.load(f)
    df = _to_dataframe(obj)
    meta = pickle_get_metadata(filepath)
    meta['shape'] = list(df.shape)
    meta['columns'] = list(df.columns)
    return df, meta


def pickle_read_preview(filepath: str, n_rows: int = 1000) -> tuple[pd.DataFrame, dict]:
    df, meta = pickle_read_full(filepath)
    df = df.head(n_rows)
    meta['preview'] = True
    meta['preview_rows'] = len(df)
    return df, meta


def pickle_get_metadata(filepath: str) -> dict:
    return {
        'format': 'pickle',
        'file_size': os.path.getsize(filepath),
    }


# ═══════════════════════════════════════════════════════════════════════
#  MessagePack
# ═══════════════════════════════════════════════════════════════════════

def msgpack_read_full(filepath: str) -> tuple[pd.DataFrame, dict]:
    with open(filepath, 'rb') as f:
        obj = msgpack.unpack(f, raw=False)
    df = _to_dataframe(obj)
    meta = msgpack_get_metadata(filepath)
    meta['shape'] = list(df.shape)
    meta['columns'] = list(df.columns)
    return df, meta


def msgpack_read_preview(filepath: str, n_rows: int = 1000) -> tuple[pd.DataFrame, dict]:
    df, meta = msgpack_read_full(filepath)
    df = df.head(n_rows)
    meta['preview'] = True
    meta['preview_rows'] = len(df)
    return df, meta


def msgpack_get_metadata(filepath: str) -> dict:
    return {
        'format': 'msgpack',
        'file_size': os.path.getsize(filepath),
    }


# ═══════════════════════════════════════════════════════════════════════
#  NumPy (.npy / .npz)
# ═══════════════════════════════════════════════════════════════════════

def numpy_read_full(filepath: str, array_name: str | None = None) -> tuple[pd.DataFrame, dict]:
    loaded = np.load(filepath, allow_pickle=True)
    if isinstance(loaded, np.lib.npyio.NpzFile):
        names = list(loaded.files)
        if array_name and array_name in names:
            arr = loaded[array_name]
        else:
            arr = loaded[names[0]] if names else np.array([])
    else:
        arr = loaded
        names = None
    df = _to_dataframe(arr)
    meta = numpy_get_metadata(filepath)
    meta['shape'] = list(df.shape)
    meta['columns'] = list(df.columns)
    if names is not None:
        meta['arrays'] = names
    return df, meta


def numpy_read_preview(filepath: str, n_rows: int = 1000, array_name: str | None = None) -> tuple[pd.DataFrame, dict]:
    df, meta = numpy_read_full(filepath, array_name=array_name)
    df = df.head(n_rows)
    meta['preview'] = True
    meta['preview_rows'] = len(df)
    return df, meta


def numpy_get_metadata(filepath: str) -> dict:
    loaded = np.load(filepath, allow_pickle=True)
    if isinstance(loaded, np.lib.npyio.NpzFile):
        arrays_info = {}
        for name in loaded.files:
            arr = loaded[name]
            arrays_info[name] = {'shape': list(arr.shape), 'dtype': str(arr.dtype)}
        return {
            'format': 'numpy',
            'type': 'npz',
            'arrays': arrays_info,
            'file_size': os.path.getsize(filepath),
        }
    else:
        return {
            'format': 'numpy',
            'type': 'npy',
            'shape': list(loaded.shape),
            'dtype': str(loaded.dtype),
            'file_size': os.path.getsize(filepath),
        }


# ═══════════════════════════════════════════════════════════════════════
#  Unified dispatch
# ═══════════════════════════════════════════════════════════════════════

SERIALIZATION_DISPATCH = {
    'pickle': {
        'read_full': pickle_read_full,
        'read_preview': pickle_read_preview,
        'get_metadata': pickle_get_metadata,
    },
    'msgpack': {
        'read_full': msgpack_read_full,
        'read_preview': msgpack_read_preview,
        'get_metadata': msgpack_get_metadata,
    },
    'numpy': {
        'read_full': numpy_read_full,
        'read_preview': numpy_read_preview,
        'get_metadata': numpy_get_metadata,
    },
}


def read_full(filepath: str, format_name: str, **kwargs) -> tuple[pd.DataFrame, dict]:
    return SERIALIZATION_DISPATCH[format_name]['read_full'](filepath, **{k: v for k, v in kwargs.items() if k == 'array_name'})


def read_preview(filepath: str, format_name: str, n_rows: int = 1000, **kwargs) -> tuple[pd.DataFrame, dict]:
    fn = SERIALIZATION_DISPATCH[format_name]['read_preview']
    kw = {}
    if 'array_name' in kwargs:
        kw['array_name'] = kwargs['array_name']
    if format_name == 'numpy':
        return fn(filepath, n_rows, **kw)
    return fn(filepath, n_rows)


def get_metadata(filepath: str, format_name: str, **kwargs) -> dict:
    return SERIALIZATION_DISPATCH[format_name]['get_metadata'](filepath)
