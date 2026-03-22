"""DataPeek configuration constants."""

# Upload limits
MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500 MB upload limit
SIZE_THRESHOLD = 50 * 1024 * 1024       # 50 MB preview prompt threshold
DEFAULT_PREVIEW_ROWS = 1000
PAGINATION_PER_PAGE = 100

# Supported file extensions → format name
SUPPORTED_EXTENSIONS = {
    '.parquet': 'parquet',
    '.pq': 'parquet',
    '.feather': 'feather',
    '.arrow': 'feather',
    '.ipc': 'feather',
    '.orc': 'orc',
    '.avro': 'avro',
    '.h5': 'hdf5',
    '.hdf5': 'hdf5',
    '.he5': 'hdf5',
    '.nc': 'netcdf',
    '.nc4': 'netcdf',
    '.netcdf': 'netcdf',
    '.zarr': 'zarr',
    '.zip': 'zarr',       # Zarr ZIP store
    '.pkl': 'pickle',
    '.pickle': 'pickle',
    '.msgpack': 'msgpack',
    '.npy': 'numpy',
    '.npz': 'numpy',
    '.pt': 'pytorch',
    '.pth': 'pytorch',
    '.safetensors': 'safetensors',
    '.db': 'sqlite',
    '.sqlite': 'sqlite',
    '.sqlite3': 'sqlite',
    '.mdb': 'lmdb',
    '.lmdb': 'lmdb',
}

# All output format keys
EXPORT_FORMATS = [
    'csv', 'json', 'parquet', 'feather', 'orc', 'avro',
    'xlsx', 'hdf5', 'msgpack', 'npy', 'pickle',
]

# Sky-blue theme colours
THEME_COLORS = {
    'primary':    '#87CEEB',
    'accent':     '#5BA3CF',
    'background': '#F8FBFD',
    'text':       '#2C3E50',
    'border':     '#D6E9F5',
    'error':      '#E74C3C',
    'success':    '#27AE60',
}
