"""Export blueprint — handles file exports and copy-to-clipboard."""

from __future__ import annotations

from flask import Blueprint, request, jsonify, send_file, current_app

from web_app.core.exporter import export_dataframe, export_to_csv_string, export_selection

export_bp = Blueprint('export', __name__)


def _dm():
    return current_app.data_manager  # type: ignore[attr-defined]


@export_bp.route('/export/full')
def export_full():
    """Export entire DataFrame as file download."""
    sid = request.sid  # type: ignore[attr-defined]
    dm = _dm()
    fmt = request.args.get('fmt', 'csv')
    if not dm.has_session(sid):
        return jsonify({'error': 'No data loaded'}), 404
    sess = dm.sessions[sid]
    df = sess['df']
    filename = sess['filename']
    base = filename.rsplit('.', 1)[0] if '.' in filename else filename
    try:
        buf, ext, mime = export_dataframe(df, fmt)
    except Exception as exc:
        return jsonify({'error': str(exc)}), 400
    return send_file(buf, mimetype=mime, as_attachment=True,
                     download_name=f'{base}_export{ext}')


@export_bp.route('/export/selection', methods=['POST'])
def export_sel():
    """Export a rectangular selection as file download."""
    sid = request.sid  # type: ignore[attr-defined]
    dm = _dm()
    if not dm.has_session(sid):
        return jsonify({'error': 'No data loaded'}), 404
    body = request.get_json(silent=True) or {}
    fmt = body.get('fmt', 'csv')
    row_start = int(body.get('row_start', 0))
    row_end = int(body.get('row_end', 0))
    col_start = int(body.get('col_start', 0))
    col_end = int(body.get('col_end', 0))
    sess = dm.sessions[sid]
    df = sess['df']
    filename = sess['filename']
    base = filename.rsplit('.', 1)[0] if '.' in filename else filename
    try:
        buf, ext, mime = export_selection(df, row_start, row_end, col_start, col_end, fmt)
    except Exception as exc:
        return jsonify({'error': str(exc)}), 400
    return send_file(buf, mimetype=mime, as_attachment=True,
                     download_name=f'{base}_selection{ext}')


@export_bp.route('/copy', methods=['POST'])
def copy_csv():
    """Return CSV text for clipboard."""
    sid = request.sid  # type: ignore[attr-defined]
    dm = _dm()
    if not dm.has_session(sid):
        return jsonify({'error': 'No data loaded'}), 404
    body = request.get_json(silent=True) or {}
    row_start = int(body.get('row_start', 0))
    row_end = int(body.get('row_end', 0))
    col_start = int(body.get('col_start', 0))
    col_end = int(body.get('col_end', 0))
    df = dm.get_selection(sid, row_start, row_end, col_start, col_end)
    csv_text = export_to_csv_string(df)
    return jsonify({'csv_text': csv_text})


@export_bp.route('/reset', methods=['POST'])
def reset():
    """Purge session and redirect to upload page."""
    sid = request.sid  # type: ignore[attr-defined]
    dm = _dm()
    dm.purge(sid)
    return jsonify({'redirect': '/'})
