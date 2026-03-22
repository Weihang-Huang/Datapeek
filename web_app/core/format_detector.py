"""Auto-detect binary data file format via magic bytes and file extension."""

from __future__ import annotations

import os
import struct
import zipfile
import io

from web_app.config import SUPPORTED_EXTENSIONS


def detect_format(filename: str, file_bytes: bytes) -> str | None:
    """Return a format string (e.g. 'parquet', 'hdf5') or None if unrecognised.

    Detection strategy:
    1. Check magic bytes / signatures in the file header.
    2. Fall back to file extension lookup.
    """
    fmt = _detect_by_magic(file_bytes, filename)
    if fmt:
        return fmt

    # Fallback: extension-based detection
    ext = os.path.splitext(filename)[1].lower()
    return SUPPORTED_EXTENSIONS.get(ext)


def _detect_by_magic(data: bytes, filename: str) -> str | None:
    """Attempt to identify format from the raw bytes."""
    if len(data) < 4:
        return None

    # ── Parquet: starts with PAR1 ────────────────────────────────────
    if data[:4] == b'PAR1':
        return 'parquet'

    # ── Feather / Arrow IPC: starts with ARROW1 ─────────────────────
    if data[:6] == b'ARROW1':
        return 'feather'

    # ── ORC: starts with ORC ─────────────────────────────────────────
    if data[:3] == b'ORC':
        return 'orc'

    # ── Avro: Object Container File starts with Obj\x01 ─────────────
    if data[:4] == b'Obj\x01':
        return 'avro'

    # ── HDF5: \x89HDF\r\n\x1a\n ──────────────────────────────────────
    if data[:8] == b'\x89HDF\r\n\x1a\n':
        return 'hdf5'

    # ── NetCDF classic: CDF\x01 or CDF\x02 ──────────────────────────
    if data[:4] in (b'CDF\x01', b'CDF\x02'):
        return 'netcdf'

    # ── NumPy: \x93NUMPY ─────────────────────────────────────────────
    if data[:6] == b'\x93NUMPY':
        return 'numpy'

    # ── SQLite: 'SQLite format 3\x00' (first 16 bytes) ──────────────
    if data[:16] == b'SQLite format 3\x00':
        return 'sqlite'

    # ── ZIP-based formats (Zarr ZIP store, PyTorch .pt) ──────────────
    if data[:4] == b'PK\x03\x04':
        # Try to distinguish PyTorch from Zarr
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                names = zf.namelist()
                if any(n.startswith('archive/') for n in names):
                    return 'pytorch'
                # Check for Zarr metadata
                if any('.zarray' in n or '.zgroup' in n or '.zattrs' in n for n in names):
                    return 'zarr'
        except (zipfile.BadZipFile, Exception):
            pass
        # Fall through to extension-based
        ext = os.path.splitext(filename)[1].lower()
        if ext in ('.pt', '.pth'):
            return 'pytorch'
        if ext in ('.zarr', '.zip'):
            return 'zarr'
        return None

    # ── Pickle: protocol 4 (\x80\x04\x95) or protocol 5 (\x80\x05\x95)
    if len(data) >= 3 and data[0:1] == b'\x80' and data[1:2] in (b'\x04', b'\x05') and data[2:3] == b'\x95':
        return 'pickle'

    # ── SafeTensors: first 8 bytes are LE u64 JSON header length ─────
    if len(data) >= 8:
        ext = os.path.splitext(filename)[1].lower()
        if ext == '.safetensors':
            try:
                header_len = struct.unpack('<Q', data[:8])[0]
                if 0 < header_len < len(data):
                    # Peek at JSON header
                    snippet = data[8:8 + min(header_len, 32)]
                    if snippet.startswith(b'{'):
                        return 'safetensors'
            except Exception:
                pass

    # No magic-byte match
    return None
