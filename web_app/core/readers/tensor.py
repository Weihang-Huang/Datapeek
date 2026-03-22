"""Readers for tensor/ML formats: SafeTensors, PyTorch (.pt).

No torch or tensorflow dependency — PyTorch files are read via
zipfile + pickle + numpy (the standard PyTorch serialisation format
stores tensors as numpy-compatible data inside a ZIP archive).
"""

from __future__ import annotations

import io
import os
import pickle
import struct
import zipfile

import numpy as np
import pandas as pd


def _tensor_summary_row(name: str, arr: np.ndarray) -> dict:
    """Build one summary row for a tensor."""
    try:
        flat = arr.astype(float).flatten() if arr.size > 0 else np.array([0.0])
    except (ValueError, TypeError):
        flat = np.array([0.0])
    return {
        'name': name,
        'shape': str(list(arr.shape)),
        'dtype': str(arr.dtype),
        'numel': int(arr.size),
        'min': float(np.nanmin(flat)) if flat.size else None,
        'max': float(np.nanmax(flat)) if flat.size else None,
        'mean': float(np.nanmean(flat)) if flat.size else None,
        'std': float(np.nanstd(flat)) if flat.size else None,
    }


_EMPTY_SUMMARY = pd.DataFrame(
    columns=['name', 'shape', 'dtype', 'numel', 'min', 'max', 'mean', 'std']
)


# ═══════════════════════════════════════════════════════════════════════
#  SafeTensors  (via safetensors.numpy — no torch needed)
# ═══════════════════════════════════════════════════════════════════════

def safetensors_read_full(filepath: str) -> tuple[pd.DataFrame, dict]:
    from safetensors.numpy import load_file
    tensors = load_file(filepath)
    rows = [_tensor_summary_row(name, arr) for name, arr in tensors.items()]
    df = pd.DataFrame(rows) if rows else _EMPTY_SUMMARY.copy()
    return df, safetensors_get_metadata(filepath)


def safetensors_read_preview(filepath: str, n_rows: int = 1000) -> tuple[pd.DataFrame, dict]:
    df, meta = safetensors_read_full(filepath)
    df = df.head(n_rows)
    meta['preview'] = True
    meta['preview_rows'] = len(df)
    return df, meta


def safetensors_get_metadata(filepath: str) -> dict:
    from safetensors.numpy import load_file
    tensors = load_file(filepath)
    info = [{'name': n, 'shape': list(a.shape), 'dtype': str(a.dtype)}
            for n, a in tensors.items()]
    return {
        'format': 'safetensors',
        'tensor_view': True,
        'tensors': info,
        'file_size': os.path.getsize(filepath),
    }


# ═══════════════════════════════════════════════════════════════════════
#  PyTorch .pt  (pure Python — no torch import)
#
#  PyTorch's standard save format is a ZIP archive that contains:
#    archive/data.pkl          — pickled structure referencing storage objects
#    archive/data/0, 1, …      — raw tensor bytes
#
#  We use a custom Unpickler that reconstructs torch.Tensor objects as
#  plain numpy arrays by reading the raw bytes from the ZIP.
# ═══════════════════════════════════════════════════════════════════════

# Numpy dtype for each torch storage type
_TORCH_DTYPE_MAP = {
    'torch.FloatStorage':   np.float32,
    'torch.DoubleStorage':  np.float64,
    'torch.HalfStorage':    np.float16,
    'torch.BFloat16Storage': np.dtype('V2'),  # bfloat16 → raw 2-byte
    'torch.IntStorage':     np.int32,
    'torch.LongStorage':    np.int64,
    'torch.ShortStorage':   np.int16,
    'torch.ByteStorage':    np.uint8,
    'torch.CharStorage':    np.int8,
    'torch.BoolStorage':    np.bool_,
    'torch.ComplexFloatStorage':  np.complex64,
    'torch.ComplexDoubleStorage': np.complex128,
}


class _TorchUnpickler(pickle.Unpickler):
    """Unpickler that converts torch storage → numpy arrays without torch."""

    def __init__(self, fp, zip_file: zipfile.ZipFile):
        super().__init__(fp)
        self._zip = zip_file

    def find_class(self, module: str, name: str):
        # Intercept torch rebuild functions
        if module == 'torch._utils' and name == '_rebuild_tensor_v2':
            return self._rebuild_tensor_v2
        if module == 'torch._utils' and name == '_rebuild_tensor_v3':
            return self._rebuild_tensor_v3
        if module == 'torch' and name == 'BFloat16Storage':
            return lambda *a, **kw: None
        # Return a dummy for any torch class so pickle doesn't crash
        if module.startswith('torch'):
            return _Dummy
        # collections.OrderedDict etc.
        return super().find_class(module, name)

    def persistent_load(self, saved_id):
        """Handle PersistentID references to raw tensor data files."""
        if not isinstance(saved_id, tuple) or len(saved_id) < 5:
            return saved_id
        # saved_id = ('storage', storage_type, key, location, numel)
        _, storage_type_obj, key, _location, numel = saved_id[:5]
        # storage_type_obj might be a class or a string representation
        type_name = (storage_type_obj.__name__
                     if hasattr(storage_type_obj, '__name__')
                     else str(storage_type_obj))
        full_name = f'torch.{type_name}' if not type_name.startswith('torch.') else type_name

        dtype = _TORCH_DTYPE_MAP.get(full_name, np.float32)

        # Read raw bytes from the ZIP archive
        for prefix in ('archive/data/', 'data/'):
            path = f'{prefix}{key}'
            if path in self._zip.namelist():
                raw = self._zip.read(path)
                arr = np.frombuffer(raw, dtype=dtype)[:int(numel)]
                return arr

        return np.zeros(int(numel), dtype=dtype)

    @staticmethod
    def _rebuild_tensor_v2(storage, storage_offset, size, stride, *rest):
        """Reconstruct a tensor from storage + metadata."""
        if not isinstance(storage, np.ndarray):
            return np.zeros(size)
        try:
            offset = int(storage_offset)
            total = 1
            for s in size:
                total *= s
            flat = storage[offset:offset + total]
            return flat.reshape(size)
        except Exception:
            return storage

    @staticmethod
    def _rebuild_tensor_v3(storage, storage_offset, size, stride, *rest):
        return _TorchUnpickler._rebuild_tensor_v2(storage, storage_offset, size, stride, *rest)


class _Dummy:
    """Stand-in for any torch class during unpickling."""
    def __init__(self, *args, **kwargs):
        pass
    def __call__(self, *args, **kwargs):
        return self
    def __getattr__(self, name):
        return self


def _load_pt_file(filepath: str) -> dict[str, np.ndarray]:
    """Load a .pt file → dict of name → numpy array, without torch."""
    tensors: dict[str, np.ndarray] = {}
    with zipfile.ZipFile(filepath, 'r') as zf:
        # Find the pickle file (usually archive/data.pkl or data.pkl)
        pkl_candidates = [n for n in zf.namelist() if n.endswith('.pkl')]
        if not pkl_candidates:
            return tensors
        pkl_path = pkl_candidates[0]
        with zf.open(pkl_path) as pkl_file:
            unpickler = _TorchUnpickler(pkl_file, zf)
            obj = unpickler.load()

    # obj is typically an OrderedDict of name → ndarray
    _extract_tensors(obj, tensors, prefix='')
    return tensors


def _extract_tensors(obj, out: dict, prefix: str):
    """Recursively extract numpy arrays from the unpickled structure."""
    if isinstance(obj, dict):
        for key, val in obj.items():
            _extract_tensors(val, out, f'{prefix}{key}.')
    elif isinstance(obj, np.ndarray) and obj.size > 0:
        name = prefix.rstrip('.') or 'tensor'
        out[name] = obj
    elif isinstance(obj, (list, tuple)):
        for i, item in enumerate(obj):
            _extract_tensors(item, out, f'{prefix}[{i}].')


def pytorch_read_full(filepath: str) -> tuple[pd.DataFrame, dict]:
    tensors = _load_pt_file(filepath)
    rows = [_tensor_summary_row(name, arr) for name, arr in tensors.items()]
    df = pd.DataFrame(rows) if rows else _EMPTY_SUMMARY.copy()
    return df, pytorch_get_metadata(filepath)


def pytorch_read_preview(filepath: str, n_rows: int = 1000) -> tuple[pd.DataFrame, dict]:
    df, meta = pytorch_read_full(filepath)
    df = df.head(n_rows)
    meta['preview'] = True
    meta['preview_rows'] = len(df)
    return df, meta


def pytorch_get_metadata(filepath: str) -> dict:
    tensors = _load_pt_file(filepath)
    info = [{'name': n, 'shape': list(a.shape), 'dtype': str(a.dtype)}
            for n, a in tensors.items()]
    return {
        'format': 'pytorch',
        'tensor_view': True,
        'tensors': info,
        'file_size': os.path.getsize(filepath),
    }


# ═══════════════════════════════════════════════════════════════════════
#  Unified dispatch  (TFRecord removed — no tensorflow dependency)
# ═══════════════════════════════════════════════════════════════════════

TENSOR_DISPATCH = {
    'safetensors': {
        'read_full': safetensors_read_full,
        'read_preview': safetensors_read_preview,
        'get_metadata': safetensors_get_metadata,
    },
    'pytorch': {
        'read_full': pytorch_read_full,
        'read_preview': pytorch_read_preview,
        'get_metadata': pytorch_get_metadata,
    },
}


def read_full(filepath: str, format_name: str, **kwargs) -> tuple[pd.DataFrame, dict]:
    return TENSOR_DISPATCH[format_name]['read_full'](filepath)


def read_preview(filepath: str, format_name: str, n_rows: int = 1000, **kwargs) -> tuple[pd.DataFrame, dict]:
    return TENSOR_DISPATCH[format_name]['read_preview'](filepath, n_rows)


def get_metadata(filepath: str, format_name: str, **kwargs) -> dict:
    return TENSOR_DISPATCH[format_name]['get_metadata'](filepath)
