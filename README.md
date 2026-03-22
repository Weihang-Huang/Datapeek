# DataPeek

New: Please get binary here. Now only windows version is available. OSX, Linux pending. https://secure.eu.internxt.com/sh/folder/pc-Q0NcmRkeSTpAe9uflbw/DtM0wOp-

**Visually inspect, edit, and export non-human-readable binary data files.**

DataPeek is a free, open-source web application that lets you upload a single binary data file, auto-detects its format, and renders its contents in an interactive spreadsheet-style visualizer. You can search, sort, edit, add/delete rows and columns, and export to multiple formats — all with zero persistence.

---

## Supported Formats (14)

| Category | Formats |
|---|---|
| **Columnar** | Parquet, Feather/Arrow IPC, ORC, Avro |
| **Hierarchical** | HDF5, NetCDF, Zarr |
| **Serialization** | Pickle, MessagePack, NumPy (.npy/.npz) |
| **ML Tensors** | PyTorch (.pt), SafeTensors |
| **Embedded Storage** | SQLite, LMDB |

---

## Features

- **Auto-detection**: Format identified via magic bytes and file extension
- **Interactive spreadsheet**: Powered by Handsontable CE (MIT)
  - Cell search, column sort, inline editing
  - Right-click context menu: add/delete rows & columns, copy as CSV
  - Paginated server-side data loading
- **Hierarchical views**: Collapsible tree sidebar for HDF5, NetCDF, Zarr
- **SQLite table selector**: Dropdown for switching between tables
- **Tensor summary**: Name, shape, dtype, numel, min, max, mean, std
- **Large file support**: Files > 50 MB prompt for Full Load or Preview mode
- **Export**: CSV, JSON, Parquet, Feather, ORC, Avro, Excel, HDF5, MessagePack, NumPy, Pickle
- **Zero persistence**: All data lives in-memory per session — purged on disconnect or new upload
- **Sky-blue theme**: Clean, minimal UI with `#87CEEB` primary colour

---

## Installation

### pip (local development)

```bash
git clone https://github.com/your-username/datapeek.git
cd datapeek
pip install -r requirements.txt
python -m web_app.app
# Open http://localhost:5000
```

### pip install (package)

```bash
pip install datapeek
datapeek                    # starts server and opens browser
datapeek myfile.parquet     # pre-loads a file
```

### Docker

```bash
docker-compose up --build
# Open http://localhost:5000
```

### Electron (desktop app)

```bash
cd electron
npm install
npm start
```

To build a standalone package:

```bash
bash scripts/build_electron.sh
```

---

## Usage

1. Open DataPeek in your browser (or Electron window)
2. Drag-and-drop or click to upload a binary data file
3. The file is auto-detected and loaded into the spreadsheet view
4. Use the toolbar to search, sort, edit, and export
5. For hierarchical files (HDF5, NetCDF, Zarr), use the tree sidebar to navigate datasets
6. For SQLite, use the table selector dropdown

### Keyboard Shortcuts

| Key | Action |
|---|---|
| `Ctrl+F` | Focus search bar |
| `Ctrl+C` | Copy selection as CSV |
| `Ctrl+S` | Open export dropdown |
| `Delete` | Delete selected rows (with confirmation) |

---

## Tech Stack

- **Backend**: Python, Flask, Blueprints
- **Readers**: pyarrow, fastavro, h5py, netCDF4, zarr, xarray, numpy, msgpack, lmdb, safetensors (PyTorch .pt files read via pure Python — no torch/tensorflow needed)
- **Frontend**: HTML5/CSS3/Vanilla JS, Handsontable CE (MIT) via CDN
- **Desktop**: Electron shell wrapping Flask
- **Remote**: Docker + Gunicorn

---

## Project Structure

```
datapeek/
├── web_app/
│   ├── app.py              # Flask app factory
│   ├── config.py           # Configuration constants
│   ├── utils.py            # Shared helpers
│   ├── core/
│   │   ├── data_manager.py # In-memory session data store
│   │   ├── exporter.py     # Export to multiple formats
│   │   ├── format_detector.py  # Magic bytes + extension detection
│   │   └── readers/        # Per-format reader modules
│   ├── routes/             # Flask blueprints (upload, data, export)
│   ├── static/             # CSS + JS
│   └── templates/          # Jinja2 HTML templates
├── electron/               # Electron shell
├── tests/                  # pytest test suite
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -am 'Add my feature'`
4. Push to the branch: `git push origin feature/my-feature`
5. Open a Pull Request

Please ensure all tests pass (`pytest tests/ -v`) before submitting.

---

## License

MIT License. See [LICENSE](LICENSE) for details.
