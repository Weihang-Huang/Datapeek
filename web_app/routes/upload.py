"""Upload blueprint — handles file uploads and format detection."""

from __future__ import annotations

import os
import tempfile

from flask import (
    Blueprint, render_template, request, jsonify, current_app,
)

from web_app.config import SIZE_THRESHOLD, SUPPORTED_EXTENSIONS, DEFAULT_PREVIEW_ROWS
from web_app.core.format_detector import detect_format
from web_app.utils import human_readable_size

upload_bp = Blueprint('upload', __name__)


def _sessions() -> dict:
    """Return the canonical sessions dict from the current app."""
    return current_app.sessions  # type: ignore[attr-defined]


def _dm():
    """Return the canonical DataManager from the current app."""
    return current_app.data_manager  # type: ignore[attr-defined]


@upload_bp.route('/')
def index():
    """Render the upload page."""
    return render_template('upload.html')


@upload_bp.route('/upload', methods=['POST'])
def upload_file():
    """Receive an uploaded file, detect format, optionally prompt for size."""
    f = request.files.get('file')
    if not f or not f.filename:
        return jsonify({'error': 'No file provided'}), 400

    filename = f.filename
    ext = os.path.splitext(filename)[1].lower()

    # Extension whitelist
    if ext not in SUPPORTED_EXTENSIONS:
        supported = ', '.join(sorted(SUPPORTED_EXTENSIONS.keys()))
        return jsonify({'error': f'Unsupported extension "{ext}". Supported: {supported}'}), 400

    file_bytes = f.read()
    f.seek(0)

    fmt = detect_format(filename, file_bytes)
    if fmt is None:
        return jsonify({'error': 'Unsupported file format — could not identify the file.'}), 400

    file_size = len(file_bytes)
    sid = request.sid  # type: ignore[attr-defined]

    # Save to temp file so readers can work with a path
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    tmp.write(file_bytes)
    tmp.close()

    # Stash temp path and format in sessions dict for /upload/confirm
    sess = _sessions()
    if sid not in sess:
        sess[sid] = {}
    sess[sid]['pending'] = {
        'filepath': tmp.name,
        'filename': filename,
        'format': fmt,
        'size': file_size,
    }

    if file_size > SIZE_THRESHOLD:
        return jsonify({
            'prompt': True,
            'size': human_readable_size(file_size),
            'format': fmt,
        })

    # Auto full-load
    dm = _dm()
    try:
        dm.load_file(sid, tmp.name, filename, fmt, mode='full')
    except Exception as exc:
        return jsonify({'error': f'Failed to parse file: {exc}'}), 400

    return jsonify({'redirect': '/view'})


@upload_bp.route('/upload/confirm', methods=['POST'])
def upload_confirm():
    """Handle user's choice after the size prompt."""
    sid = request.sid  # type: ignore[attr-defined]
    sess = _sessions()
    pending = sess.get(sid, {}).get('pending')
    if not pending:
        return jsonify({'error': 'No pending upload found — please upload again.'}), 400

    data = request.get_json(silent=True) or {}
    mode = data.get('mode', 'full')
    n_rows = int(data.get('n_rows', DEFAULT_PREVIEW_ROWS))

    dm = _dm()
    try:
        dm.load_file(
            sid,
            pending['filepath'],
            pending['filename'],
            pending['format'],
            mode=mode,
            n_rows=n_rows,
        )
    except Exception as exc:
        return jsonify({'error': f'Failed to parse file: {exc}'}), 400

    return jsonify({'redirect': '/view'})
