"""Readers for columnar binary formats: Parquet, Feather, ORC, Avro."""

from __future__ import annotations

import io
import os

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.feather as feather_mod
import pyarrow.orc as orc_mod
import fastavro


# ═══════════════════════════════════════════════════════════════════════
#  Parquet
# ═══════════════════════════════════════════════════════════════════════

def parquet_read_full(filepath: str) -> tuple[pd.DataFrame, dict]:
    table = pq.read_table(filepath)
    df = table.to_pandas()
    meta = parquet_get_metadata(filepath)
    return df, meta


def parquet_read_preview(filepath: str, n_rows: int = 1000) -> tuple[pd.DataFrame, dict]:
    pf = pq.ParquetFile(filepath)
    rows_read = 0
    batches = []
    for batch in pf.iter_batches(batch_size=min(n_rows, 10_000)):
        batches.append(batch)
        rows_read += batch.num_rows
        if rows_read >= n_rows:
            break
    table = pa.Table.from_batches(batches)
    df = table.to_pandas().head(n_rows)
    meta = parquet_get_metadata(filepath)
    meta['preview'] = True
    meta['preview_rows'] = len(df)
    return df, meta


def parquet_get_metadata(filepath: str) -> dict:
    pf = pq.ParquetFile(filepath)
    schema = pf.schema_arrow
    md = pf.metadata
    return {
        'format': 'parquet',
        'columns': [f.name for f in schema],
        'dtypes': {f.name: str(f.type) for f in schema},
        'shape': (md.num_rows, md.num_columns),
        'compression': str(md.row_group(0).column(0).compression) if md.num_row_groups > 0 else 'unknown',
        'row_group_count': md.num_row_groups,
        'file_size': os.path.getsize(filepath),
    }


# ═══════════════════════════════════════════════════════════════════════
#  Feather / Arrow IPC
# ═══════════════════════════════════════════════════════════════════════

def feather_read_full(filepath: str) -> tuple[pd.DataFrame, dict]:
    df = feather_mod.read_feather(filepath)
    meta = feather_get_metadata(filepath)
    return df, meta


def feather_read_preview(filepath: str, n_rows: int = 1000) -> tuple[pd.DataFrame, dict]:
    table = feather_mod.read_table(filepath)
    df = table.to_pandas().head(n_rows)
    meta = feather_get_metadata(filepath)
    meta['preview'] = True
    meta['preview_rows'] = len(df)
    return df, meta


def feather_get_metadata(filepath: str) -> dict:
    table = feather_mod.read_table(filepath)
    schema = table.schema
    return {
        'format': 'feather',
        'columns': [f.name for f in schema],
        'dtypes': {f.name: str(f.type) for f in schema},
        'shape': (table.num_rows, table.num_columns),
        'file_size': os.path.getsize(filepath),
    }


# ═══════════════════════════════════════════════════════════════════════
#  ORC
# ═══════════════════════════════════════════════════════════════════════

def orc_read_full(filepath: str) -> tuple[pd.DataFrame, dict]:
    table = orc_mod.read_table(filepath)
    df = table.to_pandas()
    meta = orc_get_metadata(filepath)
    return df, meta


def orc_read_preview(filepath: str, n_rows: int = 1000) -> tuple[pd.DataFrame, dict]:
    table = orc_mod.read_table(filepath)
    df = table.to_pandas().head(n_rows)
    meta = orc_get_metadata(filepath)
    meta['preview'] = True
    meta['preview_rows'] = len(df)
    return df, meta


def orc_get_metadata(filepath: str) -> dict:
    orc_file = orc_mod.ORCFile(filepath)
    schema = orc_file.schema
    return {
        'format': 'orc',
        'columns': [f.name for f in schema],
        'dtypes': {f.name: str(f.type) for f in schema},
        'shape': (orc_file.nrows, len(schema)),
        'compression': str(orc_file.compression),
        'file_size': os.path.getsize(filepath),
    }


# ═══════════════════════════════════════════════════════════════════════
#  Avro
# ═══════════════════════════════════════════════════════════════════════

def avro_read_full(filepath: str) -> tuple[pd.DataFrame, dict]:
    with open(filepath, 'rb') as f:
        reader = fastavro.reader(f)
        schema = reader.writer_schema
        records = list(reader)
    df = pd.DataFrame(records)
    meta = _avro_meta(schema, df, filepath)
    return df, meta


def avro_read_preview(filepath: str, n_rows: int = 1000) -> tuple[pd.DataFrame, dict]:
    records = []
    with open(filepath, 'rb') as f:
        reader = fastavro.reader(f)
        schema = reader.writer_schema
        for i, rec in enumerate(reader):
            if i >= n_rows:
                break
            records.append(rec)
    df = pd.DataFrame(records)
    meta = _avro_meta(schema, df, filepath)
    meta['preview'] = True
    meta['preview_rows'] = len(df)
    return df, meta


def avro_get_metadata(filepath: str) -> dict:
    with open(filepath, 'rb') as f:
        reader = fastavro.reader(f)
        schema = reader.writer_schema
        count = sum(1 for _ in reader)
    return {
        'format': 'avro',
        'columns': [field['name'] for field in schema.get('fields', [])],
        'dtypes': {field['name']: str(field['type']) for field in schema.get('fields', [])},
        'shape': (count, len(schema.get('fields', []))),
        'file_size': os.path.getsize(filepath),
    }


def _avro_meta(schema, df, filepath):
    fields = schema.get('fields', []) if schema else []
    return {
        'format': 'avro',
        'columns': [f['name'] for f in fields],
        'dtypes': {f['name']: str(f['type']) for f in fields},
        'shape': tuple(df.shape),
        'file_size': os.path.getsize(filepath),
    }


# ═══════════════════════════════════════════════════════════════════════
#  Unified dispatch helpers
# ═══════════════════════════════════════════════════════════════════════

COLUMNAR_DISPATCH = {
    'parquet': {
        'read_full': parquet_read_full,
        'read_preview': parquet_read_preview,
        'get_metadata': parquet_get_metadata,
    },
    'feather': {
        'read_full': feather_read_full,
        'read_preview': feather_read_preview,
        'get_metadata': feather_get_metadata,
    },
    'orc': {
        'read_full': orc_read_full,
        'read_preview': orc_read_preview,
        'get_metadata': orc_get_metadata,
    },
    'avro': {
        'read_full': avro_read_full,
        'read_preview': avro_read_preview,
        'get_metadata': avro_get_metadata,
    },
}


def read_full(filepath: str, format_name: str, **kwargs) -> tuple[pd.DataFrame, dict]:
    return COLUMNAR_DISPATCH[format_name]['read_full'](filepath)


def read_preview(filepath: str, format_name: str, n_rows: int = 1000, **kwargs) -> tuple[pd.DataFrame, dict]:
    return COLUMNAR_DISPATCH[format_name]['read_preview'](filepath, n_rows)


def get_metadata(filepath: str, format_name: str, **kwargs) -> dict:
    return COLUMNAR_DISPATCH[format_name]['get_metadata'](filepath)
