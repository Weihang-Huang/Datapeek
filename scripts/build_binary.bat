@echo off
REM Build DataPeek binary for Windows using PyInstaller.
REM Usage: scripts\build_binary.bat  (from the datapeek root folder)

cd /d "%~dp0\.."

echo === Checking Python ===
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.10+ and ensure it is on PATH.
    exit /b 1
)

echo === Installing dependencies ===
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

echo.
echo === Building with PyInstaller ===
python -m PyInstaller ^
    --onedir ^
    --name datapeek ^
    --add-data "web_app/templates;web_app/templates" ^
    --add-data "web_app/static;web_app/static" ^
    --hidden-import web_app ^
    --hidden-import web_app.app ^
    --hidden-import web_app.config ^
    --hidden-import web_app.utils ^
    --hidden-import web_app.cli ^
    --hidden-import web_app.routes ^
    --hidden-import web_app.routes.upload ^
    --hidden-import web_app.routes.data ^
    --hidden-import web_app.routes.export ^
    --hidden-import web_app.core ^
    --hidden-import web_app.core.format_detector ^
    --hidden-import web_app.core.data_manager ^
    --hidden-import web_app.core.exporter ^
    --hidden-import web_app.core.readers ^
    --hidden-import web_app.core.readers.columnar ^
    --hidden-import web_app.core.readers.hierarchical ^
    --hidden-import web_app.core.readers.serialization ^
    --hidden-import web_app.core.readers.tensor ^
    --hidden-import web_app.core.readers.storage ^
    --hidden-import pyarrow ^
    --hidden-import pyarrow.parquet ^
    --hidden-import pyarrow.feather ^
    --hidden-import pyarrow.orc ^
    --hidden-import fastavro ^
    --hidden-import h5py ^
    --hidden-import netCDF4 ^
    --hidden-import zarr ^
    --hidden-import xarray ^
    --hidden-import numpy ^
    --hidden-import pandas ^
    --hidden-import msgpack ^
    --hidden-import lmdb ^
    --hidden-import safetensors ^
    --hidden-import safetensors.numpy ^
    --hidden-import openpyxl ^
    --hidden-import tables ^
    --hidden-import flask ^
    --hidden-import gunicorn ^
    --collect-submodules pyarrow ^
    --collect-submodules pandas ^
    --collect-submodules numpy ^
    --collect-submodules flask ^
    --collect-submodules xarray ^
    --collect-submodules zarr ^
    --collect-data xarray ^
    --collect-data zarr ^
    web_app/cli.py

echo.
echo === Build complete! ===
echo Binary is at: dist\datapeek\
echo.
echo To run:  dist\datapeek\datapeek.exe
echo To run with a file:  dist\datapeek\datapeek.exe myfile.parquet
pause
