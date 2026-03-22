"""DataPeek exporter — convert DataFrames to various output formats in memory."""

from __future__ import annotations

import io

import numpy as np
import pandas as pd


def export_dataframe(df: pd.DataFrame, fmt: str) -> tuple[io.BytesIO, str, str]:
    """Export *df* to format *fmt*.

    Returns (buffer, filename_ext, mime_type).
    The buffer is a BytesIO ready for streaming to the client.
    """
    buf = io.BytesIO()

    if fmt == 'csv':
        buf.write(df.to_csv(index=False).encode('utf-8'))
        return _finish(buf, '.csv', 'text/csv')

    if fmt == 'json':
        buf.write(df.to_json(orient='records', indent=2).encode('utf-8'))
        return _finish(buf, '.json', 'application/json')

    if fmt == 'parquet':
        df.to_parquet(buf, index=False)
        return _finish(buf, '.parquet', 'application/octet-stream')

    if fmt == 'feather':
        import pyarrow.feather as feather_mod
        feather_mod.write_feather(df, buf)
        return _finish(buf, '.feather', 'application/octet-stream')

    if fmt == 'orc':
        import pyarrow as pa
        import pyarrow.orc as orc_mod
        table = pa.Table.from_pandas(df)
        orc_mod.write_table(table, buf)
        return _finish(buf, '.orc', 'application/octet-stream')

    if fmt == 'avro':
        import fastavro
        records = df.fillna('').to_dict(orient='records')
        fields = []
        for col in df.columns:
            dtype = str(df[col].dtype)
            if 'int' in dtype:
                avro_type = ['null', 'long']
            elif 'float' in dtype:
                avro_type = ['null', 'double']
            elif 'bool' in dtype:
                avro_type = ['null', 'boolean']
            else:
                avro_type = ['null', 'string']
            fields.append({'name': str(col), 'type': avro_type})
        schema = {'type': 'record', 'name': 'Export', 'fields': fields}
        # Coerce values to match schema
        clean_records = []
        for rec in records:
            clean = {}
            for col in df.columns:
                val = rec[str(col)]
                dtype = str(df[col].dtype)
                if 'int' in dtype:
                    try:
                        clean[str(col)] = int(val) if val != '' else None
                    except (ValueError, TypeError):
                        clean[str(col)] = None
                elif 'float' in dtype:
                    try:
                        clean[str(col)] = float(val) if val != '' else None
                    except (ValueError, TypeError):
                        clean[str(col)] = None
                elif 'bool' in dtype:
                    clean[str(col)] = bool(val) if val != '' else None
                else:
                    clean[str(col)] = str(val) if val is not None else None
            clean_records.append(clean)
        fastavro.writer(buf, schema, clean_records)
        return _finish(buf, '.avro', 'application/octet-stream')

    if fmt == 'xlsx':
        df.to_excel(buf, index=False, engine='openpyxl')
        return _finish(buf, '.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    if fmt == 'hdf5':
        # Write to a temp BytesIO via pd.HDFStore
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix='.h5', delete=False) as tmp:
            tmp_path = tmp.name
        try:
            df.to_hdf(tmp_path, key='data', mode='w')
            with open(tmp_path, 'rb') as f:
                buf.write(f.read())
        finally:
            os.unlink(tmp_path)
        return _finish(buf, '.h5', 'application/octet-stream')

    if fmt == 'msgpack':
        import msgpack
        data = df.fillna('').to_dict(orient='records')
        buf.write(msgpack.packb(data, use_bin_type=True))
        return _finish(buf, '.msgpack', 'application/octet-stream')

    if fmt == 'npy':
        np.save(buf, df.values)
        return _finish(buf, '.npy', 'application/octet-stream')

    if fmt == 'pickle':
        df.to_pickle(buf)
        return _finish(buf, '.pkl', 'application/octet-stream')

    raise ValueError(f'Unsupported export format: {fmt}')


def export_to_csv_string(df: pd.DataFrame) -> str:
    """Return CSV text for the clipboard copy feature."""
    return df.to_csv(index=False, sep='\t')


def export_selection(df: pd.DataFrame, row_start: int, row_end: int,
                     col_start: int, col_end: int, fmt: str) -> tuple[io.BytesIO, str, str]:
    """Slice the DataFrame, then export the selection."""
    sliced = df.iloc[row_start:row_end, col_start:col_end]
    return export_dataframe(sliced, fmt)


def _finish(buf: io.BytesIO, ext: str, mime: str) -> tuple[io.BytesIO, str, str]:
    buf.seek(0)
    return buf, ext, mime
