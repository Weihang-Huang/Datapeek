"""Readers for hierarchical formats: HDF5, NetCDF, Zarr."""

from __future__ import annotations

import os
from typing import Any

import numpy as np
import pandas as pd


# ═══════════════════════════════════════════════════════════════════════
#  HDF5
# ═══════════════════════════════════════════════════════════════════════

def _hdf5_tree(group) -> list[dict]:
    """Recursively build a tree of groups and datasets from an h5py group."""
    import h5py
    children = []
    for key in group.keys():
        item = group[key]
        if isinstance(item, h5py.Group):
            children.append({
                'name': key,
                'path': item.name,
                'type': 'group',
                'children': _hdf5_tree(item),
            })
        elif isinstance(item, h5py.Dataset):
            children.append({
                'name': key,
                'path': item.name,
                'type': 'dataset',
                'shape': list(item.shape),
                'dtype': str(item.dtype),
            })
    return children


def _hdf5_first_dataset(group) -> str | None:
    """Return the path of the first leaf dataset found via DFS."""
    import h5py
    for key in group.keys():
        item = group[key]
        if isinstance(item, h5py.Dataset):
            return item.name
        elif isinstance(item, h5py.Group):
            found = _hdf5_first_dataset(item)
            if found:
                return found
    return None


def hdf5_read_full(filepath: str, path: str | None = None) -> tuple[pd.DataFrame, dict]:
    import h5py
    with h5py.File(filepath, 'r') as f:
        if path is None:
            path = _hdf5_first_dataset(f)
        if path is None:
            return pd.DataFrame(), hdf5_get_metadata(filepath)
        ds = f[path]
        data = ds[()]
    if isinstance(data, np.ndarray):
        if data.ndim == 1:
            df = pd.DataFrame(data, columns=[path.split('/')[-1]])
        elif data.ndim == 2:
            df = pd.DataFrame(data)
        else:
            df = pd.DataFrame(data.reshape(data.shape[0], -1))
    else:
        df = pd.DataFrame([data])
    meta = hdf5_get_metadata(filepath)
    meta['active_path'] = path
    return df, meta


def hdf5_read_preview(filepath: str, n_rows: int = 1000, path: str | None = None) -> tuple[pd.DataFrame, dict]:
    df, meta = hdf5_read_full(filepath, path=path)
    df = df.head(n_rows)
    meta['preview'] = True
    meta['preview_rows'] = len(df)
    return df, meta


def hdf5_get_metadata(filepath: str) -> dict:
    import h5py
    with h5py.File(filepath, 'r') as f:
        tree = _hdf5_tree(f)
    return {
        'format': 'hdf5',
        'tree': tree,
        'file_size': os.path.getsize(filepath),
        'hierarchical': True,
    }


# ═══════════════════════════════════════════════════════════════════════
#  NetCDF
# ═══════════════════════════════════════════════════════════════════════

def netcdf_read_full(filepath: str, path: str | None = None) -> tuple[pd.DataFrame, dict]:
    import xarray as xr
    ds = xr.open_dataset(filepath)
    if path and path in ds.data_vars:
        df = ds[[path]].to_dataframe().reset_index()
    else:
        df = ds.to_dataframe().reset_index()
    meta = netcdf_get_metadata(filepath)
    meta['active_path'] = path
    ds.close()
    return df, meta


def netcdf_read_preview(filepath: str, n_rows: int = 1000, path: str | None = None) -> tuple[pd.DataFrame, dict]:
    df, meta = netcdf_read_full(filepath, path=path)
    df = df.head(n_rows)
    meta['preview'] = True
    meta['preview_rows'] = len(df)
    return df, meta


def netcdf_get_metadata(filepath: str) -> dict:
    import xarray as xr
    ds = xr.open_dataset(filepath)
    tree = []
    for var_name, var in ds.data_vars.items():
        tree.append({
            'name': var_name,
            'path': var_name,
            'type': 'dataset',
            'shape': list(var.shape),
            'dtype': str(var.dtype),
        })
    for dim_name, dim in ds.dims.items():
        tree.append({
            'name': dim_name,
            'path': dim_name,
            'type': 'dimension',
            'size': int(ds.sizes[dim_name]) if hasattr(ds.sizes, '__getitem__') else int(dim),
        })
    ds.close()
    return {
        'format': 'netcdf',
        'tree': tree,
        'file_size': os.path.getsize(filepath),
        'hierarchical': True,
    }


# ═══════════════════════════════════════════════════════════════════════
#  Zarr
# ═══════════════════════════════════════════════════════════════════════

def zarr_read_full(filepath: str, path: str | None = None) -> tuple[pd.DataFrame, dict]:
    import zarr
    store = zarr.open(filepath, mode='r')
    if hasattr(store, 'keys'):
        if path and path in store:
            arr = np.asarray(store[path])
        else:
            # First array
            for key in store.keys():
                item = store[key]
                if isinstance(item, zarr.Array):
                    arr = np.asarray(item)
                    path = key
                    break
            else:
                arr = np.array([])
    elif isinstance(store, zarr.Array):
        arr = np.asarray(store)
        path = '/'
    else:
        arr = np.array([])

    if arr.ndim == 1:
        df = pd.DataFrame(arr, columns=[str(path)])
    elif arr.ndim == 2:
        df = pd.DataFrame(arr)
    elif arr.ndim == 0:
        df = pd.DataFrame([arr.item()])
    else:
        df = pd.DataFrame(arr.reshape(arr.shape[0], -1))

    meta = zarr_get_metadata(filepath)
    meta['active_path'] = path
    return df, meta


def zarr_read_preview(filepath: str, n_rows: int = 1000, path: str | None = None) -> tuple[pd.DataFrame, dict]:
    df, meta = zarr_read_full(filepath, path=path)
    df = df.head(n_rows)
    meta['preview'] = True
    meta['preview_rows'] = len(df)
    return df, meta


def _zarr_tree(group) -> list[dict]:
    import zarr
    children = []
    if not hasattr(group, 'keys'):
        return children
    for key in group.keys():
        item = group[key]
        if isinstance(item, zarr.Group):
            children.append({
                'name': key,
                'path': item.path if hasattr(item, 'path') else key,
                'type': 'group',
                'children': _zarr_tree(item),
            })
        elif isinstance(item, zarr.Array):
            children.append({
                'name': key,
                'path': item.path if hasattr(item, 'path') else key,
                'type': 'dataset',
                'shape': list(item.shape),
                'dtype': str(item.dtype),
            })
    return children


def zarr_get_metadata(filepath: str) -> dict:
    import zarr
    store = zarr.open(filepath, mode='r')
    if isinstance(store, zarr.Array):
        tree = [{
            'name': '/',
            'path': '/',
            'type': 'dataset',
            'shape': list(store.shape),
            'dtype': str(store.dtype),
        }]
    else:
        tree = _zarr_tree(store)
    return {
        'format': 'zarr',
        'tree': tree,
        'file_size': os.path.getsize(filepath) if os.path.isfile(filepath) else 0,
        'hierarchical': True,
    }


# ═══════════════════════════════════════════════════════════════════════
#  Unified dispatch
# ═══════════════════════════════════════════════════════════════════════

HIERARCHICAL_DISPATCH = {
    'hdf5': {
        'read_full': hdf5_read_full,
        'read_preview': hdf5_read_preview,
        'get_metadata': hdf5_get_metadata,
    },
    'netcdf': {
        'read_full': netcdf_read_full,
        'read_preview': netcdf_read_preview,
        'get_metadata': netcdf_get_metadata,
    },
    'zarr': {
        'read_full': zarr_read_full,
        'read_preview': zarr_read_preview,
        'get_metadata': zarr_get_metadata,
    },
}


def read_full(filepath: str, format_name: str, path: str | None = None, **kwargs) -> tuple[pd.DataFrame, dict]:
    return HIERARCHICAL_DISPATCH[format_name]['read_full'](filepath, path=path)


def read_preview(filepath: str, format_name: str, n_rows: int = 1000, path: str | None = None, **kwargs) -> tuple[pd.DataFrame, dict]:
    return HIERARCHICAL_DISPATCH[format_name]['read_preview'](filepath, n_rows, path=path)


def get_metadata(filepath: str, format_name: str, **kwargs) -> dict:
    return HIERARCHICAL_DISPATCH[format_name]['get_metadata'](filepath)
