"""Reader registry — maps format names to their reader modules."""

from __future__ import annotations

from web_app.core.readers import columnar, hierarchical, serialization, tensor, storage

READER_MAP = {
    # Columnar
    'parquet':      columnar,
    'feather':      columnar,
    'orc':          columnar,
    'avro':         columnar,
    # Hierarchical
    'hdf5':         hierarchical,
    'netcdf':       hierarchical,
    'zarr':         hierarchical,
    # Serialization
    'pickle':       serialization,
    'msgpack':      serialization,
    'numpy':        serialization,
    # Tensor / ML  (no torch or tensorflow dependency)
    'safetensors':  tensor,
    'pytorch':      tensor,
    # Storage
    'sqlite':       storage,
    'lmdb':         storage,
}


def get_reader(format_name: str):
    """Return the reader module for *format_name*, or raise KeyError."""
    return READER_MAP[format_name]
