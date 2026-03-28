# DataPeek — Implementation TODO

> **Purpose:** Step-by-step task list for an LM coding agent (OpenClaw, Perplexity Computer, etc.)
> to implement the DataPeek project from scratch.
>
> **Rules for the agent:**
> - Work through tasks **sequentially** within each phase.
> - Phases are **ordered by dependency** — complete Phase N before starting Phase N+1.
> - Each task marked with `[ ]` is a discrete unit of work. Check it off `[x]` when done.
> - If a task says "test:", write and run the test before moving on.
> - Do NOT skip tasks. If blocked, leave a `[!] BLOCKED:` note and continue to next non-dependent task.
> - Commit after each completed phase.

---

## Phase 0 — Project Scaffolding

- [ ] Create the root directory structure:
  ```
  datapeek/
  ├── electron/
  ├── web_app/
  │   ├── routes/
  │   ├── core/
  │   │   └── readers/
  │   ├── static/
  │   │   ├── css/
  │   │   └── js/
  │   └── templates/
  └── tests/
  ```
- [ ] Create `requirements.txt` with all dependencies:
  ```
  flask>=3.0
  gunicorn
  pyarrow
  fastparquet
  fastavro
  h5py
  netCDF4
  zarr
  xarray
  numpy
  pandas
  msgpack
  lmdb
  torch
  safetensors
  tensorflow
  openpyxl
  ```
- [ ] Create `web_app/config.py` with configuration constants:
  - `MAX_CONTENT_LENGTH = 500 * 1024 * 1024` (500MB upload limit)
  - `SIZE_THRESHOLD = 50 * 1024 * 1024` (50MB preview prompt threshold)
  - `DEFAULT_PREVIEW_ROWS = 1000`
  - `PAGINATION_PER_PAGE = 100`
  - `SUPPORTED_EXTENSIONS` — dict mapping each of the 15 supported extensions to format name
  - `EXPORT_FORMATS` — list of all output format keys
  - `THEME_COLORS` — dict with primary `#87CEEB`, accent `#5BA3CF`, background `#F8FBFD`, text `#2C3E50`, border `#D6E9F5`, error `#E74C3C`, success `#27AE60`
- [ ] Create `web_app/app.py` — Flask app factory:
  - Initialize Flask app
  - Register blueprints: `upload_bp`, `data_bp`, `export_bp`
  - Configure `MAX_CONTENT_LENGTH` from config
  - Add a simple session store: `sessions = {}` (module-level dict)
  - Add a `before_request` hook that assigns a session ID via cookie if not present
- [ ] Create `web_app/utils.py` with shared helpers:
  - `generate_session_id()` — random UUID string
  - `get_session(session_id)` — returns session dict or None
  - `clear_session(session_id)` — purges session data from memory
  - `human_readable_size(bytes)` — e.g. "128.4 MB"
- [ ] Test: run `flask run` and confirm the app starts with no errors and serves a blank page at `/`

---

## Phase 1 — Format Detection

- [ ] Create `web_app/core/format_detector.py`:
  - Function: `detect_format(filename: str, file_bytes: bytes) -> str | None`
  - **Step 1:** Check file extension against `SUPPORTED_EXTENSIONS` from config
  - **Step 2:** Validate using magic bytes (first 4-16 bytes) for known signatures:
    - Parquet: `PAR1` (bytes 0-3)
    - Feather/Arrow IPC: `ARROW1` (bytes 0-5)
    - ORC: `ORC` (bytes 0-2)
    - Avro: `Obj` + `0x01` (bytes 0-3)
    - HDF5: `0x89HDF0d0a1a0a` (bytes 0-7)
    - NetCDF: `CDF01` or `CDF02` (bytes 0-3)
    - NumPy: `0x93NUMPY` (bytes 0-5)
    - Pickle: `0x800495` or `0x800595` (protocol 4/5 prefix)
    - SQLite: `SQLite format 3` + null byte (bytes 0-15)
    - ZIP-based (Zarr .zip store): `PK0304` (bytes 0-3)
    - SafeTensors: first 8 bytes are little-endian u64 (JSON header length)
    - PyTorch `.pt`: ZIP archive containing `archive/` folder
    - TFRecord: no simple magic byte — rely on extension `.tfrecord`
    - MessagePack: no fixed magic — rely on extension `.msgpack`
    - LMDB: check for `data.mdb` inside directory, or rely on extension
  - **Step 3:** Return format string like `"parquet"`, `"hdf5"`, `"safetensors"`, etc. or `None` if unrecognized
- [ ] Test: write `tests/test_format_detector.py`
  - Create small sample files (even just headers) for at least 5 formats
  - Assert `detect_format()` returns the correct format string for each
  - Assert returns `None` for unsupported files (e.g. a `.txt` file)

---

## Phase 2 — Readers

Each reader module exposes a uniform interface:

```
def read_full(filepath) -> tuple[pd.DataFrame, dict]
    # Returns (dataframe, metadata_dict)

def read_preview(filepath, n_rows) -> tuple[pd.DataFrame, dict]
    # Returns (dataframe with n_rows, metadata_dict)

def get_metadata(filepath) -> dict
    # Returns schema info without loading data.
    # Must include: format, columns/keys, dtypes, shape, file_size,
    #               compression (if applicable), format-specific extras
```

### 2A — Columnar Reader
- [ ] Create `web_app/core/readers/columnar.py`
- [ ] Implement `read_full()` for Parquet using `pyarrow.parquet.read_table().to_pandas()`
- [ ] Implement `read_preview()` for Parquet — use `pq.ParquetFile` + `read_row_groups` or `head()`
- [ ] Implement `get_metadata()` for Parquet — extract schema, num_rows, num_columns, compression, row_group_count from ParquetFile metadata
- [ ] Implement `read_full()`, `read_preview()`, `get_metadata()` for Feather using `pyarrow.feather`
- [ ] Implement `read_full()`, `read_preview()`, `get_metadata()` for ORC using `pyarrow.orc`
- [ ] Implement `read_full()`, `read_preview()`, `get_metadata()` for Avro using `fastavro`; iterate records into a DataFrame
- [ ] Test: `tests/test_readers.py::TestColumnarReader` — create small sample files, assert read_full and read_preview return correct shapes and metadata

### 2B — Hierarchical Reader
- [ ] Create `web_app/core/readers/hierarchical.py`
- [ ] Implement for HDF5 using `h5py`; enumerate groups/datasets into a tree structure; for leaf datasets, convert to DataFrame
- [ ] Implement for NetCDF using `xarray.open_dataset()`; convert to DataFrame via `.to_dataframe()`
- [ ] Implement for Zarr using `zarr.open()`; enumerate groups; convert arrays to DataFrame
- [ ] For hierarchical formats, `get_metadata()` must return a tree dict with groups, datasets, shapes, and dtypes
- [ ] For `read_full()` and `read_preview()`, accept an optional `path` parameter to specify which dataset/group to load (default: first leaf dataset found)
- [ ] Test: create small HDF5 and NetCDF fixtures, assert tree structure and data loading

### 2C — Serialization Reader
- [ ] Create `web_app/core/readers/serialization.py`
- [ ] Implement for Pickle using `pd.read_pickle()`; if result is not a DataFrame, try wrapping in one (list of dicts, dict of lists, numpy array)
- [ ] Implement for MessagePack using `msgpack.unpack()`; convert to DataFrame
- [ ] Implement for NumPy using `np.load()`; if `.npz`, list arrays and load first (or selected); convert to DataFrame
- [ ] Test: create sample pkl, msgpack, npy/npz files, assert correct loading

### 2D — Tensor Reader
- [ ] Create `web_app/core/readers/tensor.py`
- [ ] Implement for SafeTensors using `safetensors.torch.load_file()` or `safetensors.numpy.load_file()`; list tensor names, shapes, dtypes; for preview, flatten to DataFrame (tensor_name, shape, dtype, min, max, mean, std)
- [ ] Implement for PyTorch `.pt` using `torch.load(weights_only=True)`; same summary approach
- [ ] Implement for TFRecord using `tf.data.TFRecordDataset`; parse first N records into DataFrame
- [ ] For tensor formats, `get_metadata()` returns a list of tensors with name/shape/dtype
- [ ] For `read_full()` and `read_preview()`, return a **summary DataFrame** (one row per tensor: name, shape, dtype, numel, min, max, mean, std) rather than flattening all values
- [ ] Test: create small safetensors and .pt files, assert summary DataFrame structure

### 2E — Storage Reader
- [ ] Create `web_app/core/readers/storage.py`
- [ ] Implement for SQLite using `sqlite3`; list tables via `sqlite_master`; `get_metadata()` returns table list + column schemas; `read_full/preview` accept a `table_name` param; default to first table
- [ ] Implement for LMDB using `lmdb`; iterate keys; attempt to decode values (pickle, msgpack, or raw bytes); build DataFrame from key-value pairs
- [ ] Test: create a small SQLite db and LMDB, assert table listing and data loading

### 2F — Reader Registry
- [ ] Create `web_app/core/readers/__init__.py` with a `READER_MAP` dict mapping format names to their reader modules, and a `get_reader(format_name)` function
- [ ] Test: assert `get_reader("parquet")` returns the columnar module, etc.

---

## Phase 3 — Data Manager

- [ ] Create `web_app/core/data_manager.py` with class `DataManager`:
  - `__init__`: initialize `self.sessions = {}` (session_id to session dict)
  - `load_file(session_id, filepath, filename, format_name, mode, n_rows=None)` — purge existing session, call reader, store DataFrame + metadata
  - `get_page(session_id, page, per_page) -> dict` — returns `{rows, total, page, pages}`
  - `search(session_id, query) -> list[dict]` — search all string-coerced cells, return `[{row, col, value}]`
  - `sort(session_id, by, ascending)` — sort by column; also support sort by row (transpose, sort, transpose back)
  - `edit_cell(session_id, row, col, value)` — mutate in-memory DataFrame
  - `add_row(session_id, position)` — insert empty row at position
  - `add_column(session_id, col_name, position, default=None)` — insert column
  - `delete_rows(session_id, row_indices)` — drop rows by index
  - `delete_columns(session_id, col_names)` — drop columns by name
  - `get_selection(session_id, row_start, row_end, col_start, col_end) -> pd.DataFrame`
  - `get_metadata(session_id) -> dict`
  - `purge(session_id)` — delete session data from memory
- [ ] `load_file()` must purge any existing session data first (one file at a time rule)
- [ ] All edit operations mutate the in-memory DataFrame directly
- [ ] Test: `tests/test_data_manager.py` — load a small parquet, test pagination, search, sort, edit, add, delete

---

## Phase 4 — Exporter

- [ ] Create `web_app/core/exporter.py` with function `export_dataframe(df, fmt, filepath)`:
- [ ] Implement export for each output format:
  - `csv` via `df.to_csv()`
  - `json` via `df.to_json(orient="records")`
  - `parquet` via `df.to_parquet()`
  - `feather` via `df.to_feather()`
  - `orc` via `df.to_orc()`
  - `avro` via convert to records + `fastavro.writer()`
  - `xlsx` via `df.to_excel()` (output-only format, requires `openpyxl`)
  - `hdf5` via `df.to_hdf()`
  - `msgpack` via `msgpack.pack(df.to_dict(orient="records"))`
  - `npy` via `np.save(df.values)`
  - `pickle` via `df.to_pickle()`
- [ ] Implement `export_to_csv_string(df) -> str` for the "copy as CSV" feature
- [ ] Implement `export_selection(df, row_range, col_range, fmt, filepath)` — slice first, then export
- [ ] All exports write to a temporary BytesIO buffer, streamed to the user and immediately discarded (no server-side persistence)
- [ ] Test: `tests/test_export.py` — round-trip: load parquet, export to csv, verify content; export to feather, read back, verify

---

## Phase 5 — Flask Routes

### 5A — Upload Route
- [ ] Create `web_app/routes/upload.py` — blueprint `upload_bp`
- [ ] `GET /` renders `upload.html`
- [ ] `POST /upload`:
  1. Receive uploaded file from `request.files`
  2. Validate extension against whitelist
  3. Call `format_detector.detect_format()` on file bytes
  4. If format is None: return JSON error `{"error": "Unsupported file format"}`
  5. Get file size; if > `SIZE_THRESHOLD`: return JSON `{"prompt": true, "size": "<human_readable>", "format": "<fmt>"}`
  6. If <= threshold: auto full-load via `data_manager.load_file()`, return JSON `{"redirect": "/view"}`
- [ ] `POST /upload/confirm`:
  1. Receive `mode` ("full" or "preview") and optional `n_rows`
  2. Call `data_manager.load_file()` with appropriate params
  3. Return JSON `{"redirect": "/view"}`

### 5B — Data Route
- [ ] Create `web_app/routes/data.py` — blueprint `data_bp`
- [ ] `GET /view` renders `visualizer.html`
- [ ] `GET /metadata` returns `data_manager.get_metadata()` as JSON
- [ ] `GET /data?page=1&per_page=100` returns `data_manager.get_page()` as JSON
- [ ] `GET /data/search?q=<query>` returns search results as JSON
- [ ] `POST /data/sort` with body `{"by": "col_name", "ascending": true}` calls `data_manager.sort()`
- [ ] `POST /data/edit` with body `{"row": 0, "col": "col_a", "value": "new"}` calls `data_manager.edit_cell()`
- [ ] `POST /data/add` with body `{"type": "row|column", "position": 0, "name": "new_col"}` calls add_row or add_column
- [ ] `POST /data/delete` with body `{"type": "row|column", "indices": [0,1]}` calls delete_rows or delete_columns

### 5C — Export Route
- [ ] Create `web_app/routes/export.py` — blueprint `export_bp`
- [ ] `GET /export/full?fmt=csv` exports entire DataFrame, returns file download via `send_file()`
- [ ] `POST /export/selection` with body `{"fmt": "csv", "row_start": 0, "row_end": 100, "col_start": 0, "col_end": 3}` exports selection as file download
- [ ] `POST /copy` with body `{"row_start": 0, "row_end": 10, "col_start": 0, "col_end": 5}` returns `{"csv_text": "..."}` for clipboard
- [ ] `POST /reset` calls `data_manager.purge()` and redirects to `/`
- [ ] Test: `tests/test_routes.py` — use Flask test client to test upload flow, data pagination, export download

---

## Phase 6 — Frontend: Upload Screen

- [ ] Create `web_app/templates/base.html`:
  - HTML5 boilerplate with meta viewport
  - Link to `style.css`
  - Sky-blue theme applied globally
  - Font: Inter (Google Fonts CDN) with system sans-serif fallback
  - Block placeholders: `title`, `content`, `scripts`
- [ ] Create `web_app/static/css/style.css`:
  - Root CSS variables: `--primary: #87CEEB; --accent: #5BA3CF; --bg: #F8FBFD; --text: #2C3E50; --border: #D6E9F5; --error: #E74C3C; --success: #27AE60;`
  - Body: background var(--bg), color var(--text), font-family Inter/sans-serif
  - Buttons: background var(--primary), border-radius 8px, no border, padding 10px 24px
  - Button hover: background var(--accent)
  - Card/container: white background, 1px solid var(--border), border-radius 8px, box-shadow 0 2px 8px rgba(0,0,0,0.06)
  - Modal overlay: semi-transparent dark backdrop
- [ ] Create `web_app/templates/upload.html`:
  - Centered card layout (max-width 560px, vertically centered)
  - App title "DataPeek" in primary color, subtle tagline beneath
  - Drag-and-drop zone: dashed border, sky-blue accent, icon, "Drop your file here or click to browse"
  - Hidden file input triggered by click on the drop zone
  - File type validation client-side (check extension before upload)
  - On file select: show filename + file size below the drop zone
  - Upload button (sky-blue, full-width of card)
  - Error display area (red text, hidden by default)
- [ ] Create `web_app/static/js/upload.js`:
  - Drag-and-drop event handlers (dragover, dragleave, drop)
  - File input change handler
  - `POST /upload` via fetch() with FormData
  - If response has `prompt: true`: show size prompt modal
  - If response has `redirect`: navigate to the redirect URL
  - If response has `error`: show error message
- [ ] Implement the size prompt modal (in upload.html + upload.js):
  - Modal overlay with centered card
  - Warning icon + file size display (e.g. "This file is 128.4 MB")
  - Radio buttons: "Full Load" / "Preview"
  - When Preview selected: show number input for row count (default 1000)
  - Cancel button (closes modal) + Continue button (POST /upload/confirm)
- [ ] Test: manually open browser, upload a small file, confirm redirect to `/view`

---

## Phase 7 — Frontend: Visualizer

- [ ] Create `web_app/templates/visualizer.html`:
  - Top bar: "DataPeek" logo (left), filename + format badge (center), close button (right)
  - Info bar: search input (left), row count + column count (right)
  - Main area: container div for the spreadsheet grid
  - Bottom bar: pagination controls (Prev / Page N of M / Next), Export dropdown button, "New Upload" button
- [ ] Integrate spreadsheet library:
  - Add Handsontable CE (MIT) via CDN or local bundle
  - Initialize with data from `/data` endpoint, column headers from `/metadata`
  - Enable: manualColumnResize, manualRowResize, contextMenu, filters, dropdownMenu
  - Enable cell editing (all cells editable by double-click)
- [ ] Create `web_app/static/js/visualizer.js`:
  - On page load: fetch `/metadata` to store schema; fetch `/data?page=1` to render table
  - Pagination: update table data when user clicks prev/next page
  - Sort: on column header click, POST `/data/sort`, re-fetch current page
  - Search: on search input (debounced 300ms), GET `/data/search?q=...`, highlight matching cells or show filtered results
  - Edit: on Handsontable `afterChange` event, POST `/data/edit` for each changed cell
  - Context menu customization:
    - "Add Row Above" / "Add Row Below" via POST `/data/add` with type row
    - "Add Column Left" / "Add Column Right" via POST `/data/add` with type column
    - "Delete Row(s)" via POST `/data/delete` with type row
    - "Delete Column(s)" via POST `/data/delete` with type column
    - "Copy Selection as CSV" via POST `/copy`, write to clipboard via `navigator.clipboard.writeText()`
  - Selection tracking: capture selected range coordinates for export/copy
- [ ] Create `web_app/static/js/export.js`:
  - Export dropdown listing all output formats: CSV, JSON, Parquet, Feather, ORC, Avro, Excel, HDF5, MessagePack, NumPy, Pickle
  - Toggle: "Full Dataset" / "Selection Only"
  - On click: GET `/export/full?fmt=X` (triggers download) or POST `/export/selection` with range + format
  - Trigger file download via dynamic anchor tag or window.open()
- [ ] Style the visualizer to match sky-blue theme:
  - Handsontable header row: background var(--primary), color white
  - Selected cells: background rgba(135,206,235,0.2)
  - Context menu: white background, sky-blue hover
  - Buttons and controls: consistent with upload screen styling
- [ ] Test: load a parquet file end-to-end, verify table renders, sort works, edit works, export downloads

---

## Phase 8 — Hierarchical & Tensor Special Views

- [ ] For hierarchical formats (HDF5, NetCDF, Zarr):
  - Add a **tree sidebar** (left panel, collapsible) in visualizer.html
  - Tree shows groups and datasets as expandable nodes
  - Clicking a leaf dataset loads it into the main table view
  - Fetch tree via `/metadata`, render with nested `<ul>` or a simple tree component
  - Style: indented nodes, folder/file icons, sky-blue highlight on selected node
- [ ] For tensor formats (SafeTensors, PyTorch, TFRecord):
  - Display the summary DataFrame (name, shape, dtype, numel, min, max, mean, std) in the main table
  - Add a **tensor detail panel**: clicking a row shows expanded info (histogram of values if small enough, full shape breakdown)
  - Tensor detail panel is optional / stretch goal — basic summary table is MVP
- [ ] For SQLite:
  - Add a **table selector dropdown** in the top bar (similar to hierarchical tree but simpler)
  - Switching tables re-fetches data from `/data?table=<name>`
- [ ] Test: load an HDF5 file with multiple groups, verify tree renders and dataset switching works

---

## Phase 9 — Electron Packaging (Local Deploy)

- [ ] Create `electron/package.json` with name "datapeek", main "main.js", electron dependency
- [ ] Create `electron/main.js`:
  - Spawn Flask backend as a child process via `child_process.spawn`
  - Wait for Flask to be ready (poll `http://127.0.0.1:5000` until responsive)
  - Create BrowserWindow pointing to `http://127.0.0.1:5000`
  - On window close: kill Flask child process
  - Set window title "DataPeek", set icon, disable default menu bar
- [ ] Create `electron/preload.js` — minimal, expose nothing unless needed
- [ ] Create a build script (`scripts/build_electron.sh` or `.bat`):
  1. `pip install pyinstaller` + `pyinstaller web_app/app.py --onefile --name datapeek-server`
  2. Copy PyInstaller output into `electron/dist/`
  3. `npx electron-builder` to package the Electron app
- [ ] Test: run `npm start` in `electron/`, verify Flask starts, Electron window opens, full workflow works
- [ ] Test: build with electron-builder, verify packaged app runs standalone without Python installed

---

## Phase 10 — Docker / Remote Deploy

- [ ] Create `Dockerfile`:
  - Base: `python:3.11-slim`
  - Copy requirements and install
  - Copy `web_app/`
  - Expose port 5000
  - CMD: gunicorn with 4 workers binding 0.0.0.0:5000
- [ ] Create `.dockerignore` excluding `electron/`, `tests/`, `__pycache__/`, `.git/`
- [ ] Create `docker-compose.yml` with service datapeek, port mapping 5000:5000, configurable MAX_CONTENT_LENGTH env var
- [ ] Test: `docker build -t datapeek .` then `docker run -p 5000:5000 datapeek`, verify full workflow in browser

---

## Phase 11 — Testing & Polish

- [ ] Ensure all test files pass: `pytest tests/ -v`
- [ ] Add error handling in every route:
  - File too large: friendly error message
  - Corrupt file: "Could not parse file" with format-specific hint
  - Unsupported format: list supported formats in error message
  - Session expired or missing: redirect to upload page
- [ ] Add loading spinners:
  - Upload: spinner on the upload button while file is transferring
  - Visualizer: spinner overlay while fetching pages, sorting, searching
- [ ] Add keyboard shortcuts:
  - `Ctrl+F` focus search bar
  - `Ctrl+C` copy selection as CSV
  - `Ctrl+S` open export dropdown
  - `Delete` delete selected rows (with confirmation)
- [ ] Cross-browser check: test in Chrome, Firefox, and Edge
- [ ] Responsive layout: ensure upload screen and visualizer work at 1024px+ width (desktop-focused, not mobile)
- [ ] Write `README.md`:
  - Project description and screenshots
  - Installation (pip, Docker, Electron)
  - Supported formats table
  - Usage examples
  - Contributing guidelines
  - License (MIT)
- [ ] Create `setup.py` / `pyproject.toml` for `pip install datapeek` distribution
- [ ] Add CLI entry point: `datapeek <filename>` starts Flask server and opens browser with file pre-loaded

---

## Phase 12 — Stretch Goals (Optional)

- [ ] Column statistics panel: click column header to show dtype, unique count, null count, min/max/mean, value distribution histogram
- [ ] Dark mode toggle (dark slate background, lighter sky-blue accents)
- [ ] Undo/redo stack for edit operations
- [ ] Multi-tab support: allow opening additional files in new tabs (separate sessions)
- [ ] Plugin architecture: allow community-contributed readers for new formats
- [ ] WASM build: explore Pyodide to run entirely in-browser without a backend
