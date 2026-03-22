#!/usr/bin/env bash
# Build DataPeek binary for the current platform using PyInstaller.
# Usage: bash scripts/build_binary.sh
#
# Works on Linux, macOS, and Windows (Git Bash / MSYS2).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

# ── Resolve Python portably ──────────────────────────────────────────
if command -v python3 &>/dev/null; then
    PY=python3
elif command -v python &>/dev/null; then
    PY=python
else
    echo "ERROR: Python not found. Install Python 3.10+ and make sure it is on PATH."
    exit 1
fi

PIP="$PY -m pip"

echo "Using Python: $($PY --version)"
echo ""

echo "=== Installing dependencies ==="
$PIP install --upgrade pip
$PIP install -r requirements.txt
$PIP install pyinstaller

# Determine path separator (: on Unix, ; on Windows/MSYS/Git Bash)
SEP=":"
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
    SEP=";"
fi

echo ""
echo "=== Building with PyInstaller ==="
$PY -m PyInstaller \
    --onedir \
    --name datapeek \
    --add-data "web_app/templates${SEP}web_app/templates" \
    --add-data "web_app/static${SEP}web_app/static" \
    --hidden-import web_app \
    --hidden-import web_app.app \
    --hidden-import web_app.config \
    --hidden-import web_app.utils \
    --hidden-import web_app.cli \
    --hidden-import web_app.routes \
    --hidden-import web_app.routes.upload \
    --hidden-import web_app.routes.data \
    --hidden-import web_app.routes.export \
    --hidden-import web_app.core \
    --hidden-import web_app.core.format_detector \
    --hidden-import web_app.core.data_manager \
    --hidden-import web_app.core.exporter \
    --hidden-import web_app.core.readers \
    --hidden-import web_app.core.readers.columnar \
    --hidden-import web_app.core.readers.hierarchical \
    --hidden-import web_app.core.readers.serialization \
    --hidden-import web_app.core.readers.tensor \
    --hidden-import web_app.core.readers.storage \
    --hidden-import pyarrow \
    --hidden-import pyarrow.parquet \
    --hidden-import pyarrow.feather \
    --hidden-import pyarrow.orc \
    --hidden-import fastavro \
    --hidden-import h5py \
    --hidden-import netCDF4 \
    --hidden-import zarr \
    --hidden-import xarray \
    --hidden-import numpy \
    --hidden-import pandas \
    --hidden-import msgpack \
    --hidden-import lmdb \
    --hidden-import safetensors \
    --hidden-import safetensors.numpy \
    --hidden-import openpyxl \
    --hidden-import tables \
    --hidden-import flask \
    --hidden-import gunicorn \
    --collect-submodules pyarrow \
    --collect-submodules pandas \
    --collect-submodules numpy \
    --collect-submodules flask \
    --collect-submodules xarray \
    --collect-submodules zarr \
    --collect-data xarray \
    --collect-data zarr \
    web_app/cli.py

echo ""
echo "=== Build complete! ==="
echo "Binary is at: dist/datapeek/"
echo ""
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
    echo "To run:  dist\\datapeek\\datapeek.exe"
    echo "To run with a file:  dist\\datapeek\\datapeek.exe myfile.parquet"
else
    echo "To run:  ./dist/datapeek/datapeek"
    echo "To run with a file:  ./dist/datapeek/datapeek myfile.parquet"
fi
