"""Readers for embedded storage formats: SQLite, LMDB."""

from __future__ import annotations

import os
import pickle as pkl
import sqlite3

import pandas as pd

try:
    import msgpack as _msgpack
except ImportError:
    _msgpack = None


# ═══════════════════════════════════════════════════════════════════════
#  SQLite
# ═══════════════════════════════════════════════════════════════════════

def sqlite_read_full(filepath: str, table_name: str | None = None) -> tuple[pd.DataFrame, dict]:
    conn = sqlite3.connect(filepath)
    tables = _sqlite_tables(conn)
    if not tables:
        conn.close()
        return pd.DataFrame(), {'format': 'sqlite', 'tables': []}
    if table_name is None or table_name not in tables:
        table_name = tables[0]
    df = pd.read_sql_query(f'SELECT * FROM "{table_name}"', conn)
    meta = sqlite_get_metadata(filepath)
    meta['active_table'] = table_name
    conn.close()
    return df, meta


def sqlite_read_preview(filepath: str, n_rows: int = 1000, table_name: str | None = None) -> tuple[pd.DataFrame, dict]:
    conn = sqlite3.connect(filepath)
    tables = _sqlite_tables(conn)
    if not tables:
        conn.close()
        return pd.DataFrame(), {'format': 'sqlite', 'tables': []}
    if table_name is None or table_name not in tables:
        table_name = tables[0]
    df = pd.read_sql_query(f'SELECT * FROM "{table_name}" LIMIT {int(n_rows)}', conn)
    meta = sqlite_get_metadata(filepath)
    meta['active_table'] = table_name
    meta['preview'] = True
    meta['preview_rows'] = len(df)
    conn.close()
    return df, meta


def sqlite_get_metadata(filepath: str) -> dict:
    conn = sqlite3.connect(filepath)
    tables = _sqlite_tables(conn)
    table_schemas = {}
    for t in tables:
        cursor = conn.execute(f'PRAGMA table_info("{t}")')
        cols = cursor.fetchall()
        table_schemas[t] = [
            {'name': c[1], 'dtype': c[2], 'nullable': not c[3], 'pk': bool(c[5])}
            for c in cols
        ]
    conn.close()
    return {
        'format': 'sqlite',
        'tables': tables,
        'table_schemas': table_schemas,
        'file_size': os.path.getsize(filepath),
        'sqlite_view': True,
    }


def _sqlite_tables(conn) -> list[str]:
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    return [row[0] for row in cursor.fetchall()]


# ═══════════════════════════════════════════════════════════════════════
#  LMDB
# ═══════════════════════════════════════════════════════════════════════

def lmdb_read_full(filepath: str) -> tuple[pd.DataFrame, dict]:
    import lmdb
    # LMDB path can be a directory or a file
    env_path = filepath
    if os.path.isfile(filepath):
        env_path = os.path.dirname(filepath) or '.'
    env = lmdb.open(env_path, readonly=True, lock=False, subdir=os.path.isdir(env_path))
    rows = []
    with env.begin() as txn:
        cursor = txn.cursor()
        for key_bytes, val_bytes in cursor:
            key = key_bytes.decode('utf-8', errors='replace')
            value = _decode_lmdb_value(val_bytes)
            rows.append({'key': key, 'value': value})
    env.close()
    df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=['key', 'value'])
    meta = lmdb_get_metadata(filepath)
    return df, meta


def lmdb_read_preview(filepath: str, n_rows: int = 1000) -> tuple[pd.DataFrame, dict]:
    import lmdb
    env_path = filepath
    if os.path.isfile(filepath):
        env_path = os.path.dirname(filepath) or '.'
    env = lmdb.open(env_path, readonly=True, lock=False, subdir=os.path.isdir(env_path))
    rows = []
    with env.begin() as txn:
        cursor = txn.cursor()
        for i, (key_bytes, val_bytes) in enumerate(cursor):
            if i >= n_rows:
                break
            key = key_bytes.decode('utf-8', errors='replace')
            value = _decode_lmdb_value(val_bytes)
            rows.append({'key': key, 'value': value})
    env.close()
    df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=['key', 'value'])
    meta = lmdb_get_metadata(filepath)
    meta['preview'] = True
    meta['preview_rows'] = len(df)
    return df, meta


def lmdb_get_metadata(filepath: str) -> dict:
    import lmdb
    env_path = filepath
    if os.path.isfile(filepath):
        env_path = os.path.dirname(filepath) or '.'
    env = lmdb.open(env_path, readonly=True, lock=False, subdir=os.path.isdir(env_path))
    with env.begin() as txn:
        count = txn.stat()['entries']
    env.close()
    return {
        'format': 'lmdb',
        'entries': count,
        'file_size': os.path.getsize(filepath) if os.path.isfile(filepath) else 0,
    }


def _decode_lmdb_value(val_bytes: bytes):
    """Try to decode an LMDB value as pickle, msgpack, or raw string."""
    # Try pickle
    try:
        return str(pkl.loads(val_bytes))
    except Exception:
        pass
    # Try msgpack
    if _msgpack:
        try:
            return str(_msgpack.unpackb(val_bytes, raw=False))
        except Exception:
            pass
    # Raw string
    try:
        return val_bytes.decode('utf-8')
    except UnicodeDecodeError:
        return val_bytes.hex()


# ═══════════════════════════════════════════════════════════════════════
#  Unified dispatch
# ═══════════════════════════════════════════════════════════════════════

STORAGE_DISPATCH = {
    'sqlite': {
        'read_full': sqlite_read_full,
        'read_preview': sqlite_read_preview,
        'get_metadata': sqlite_get_metadata,
    },
    'lmdb': {
        'read_full': lmdb_read_full,
        'read_preview': lmdb_read_preview,
        'get_metadata': lmdb_get_metadata,
    },
}


def read_full(filepath: str, format_name: str, **kwargs) -> tuple[pd.DataFrame, dict]:
    fn = STORAGE_DISPATCH[format_name]['read_full']
    if format_name == 'sqlite':
        return fn(filepath, table_name=kwargs.get('table_name'))
    return fn(filepath)


def read_preview(filepath: str, format_name: str, n_rows: int = 1000, **kwargs) -> tuple[pd.DataFrame, dict]:
    fn = STORAGE_DISPATCH[format_name]['read_preview']
    if format_name == 'sqlite':
        return fn(filepath, n_rows, table_name=kwargs.get('table_name'))
    return fn(filepath, n_rows)


def get_metadata(filepath: str, format_name: str, **kwargs) -> dict:
    return STORAGE_DISPATCH[format_name]['get_metadata'](filepath)
