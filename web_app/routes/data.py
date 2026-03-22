"""Data blueprint — serves data pages, search, sort, edit operations."""

from __future__ import annotations

from flask import Blueprint, render_template, request, jsonify, redirect, current_app

from web_app.config import PAGINATION_PER_PAGE

data_bp = Blueprint('data', __name__)


def _dm():
    return current_app.data_manager  # type: ignore[attr-defined]


@data_bp.route('/view')
def view():
    """Render the visualizer page."""
    sid = request.sid  # type: ignore[attr-defined]
    dm = _dm()
    if not dm.has_session(sid):
        return redirect('/')
    return render_template('visualizer.html')


@data_bp.route('/metadata')
def metadata():
    sid = request.sid  # type: ignore[attr-defined]
    dm = _dm()
    meta = dm.get_metadata(sid)
    if meta is None:
        return jsonify({'error': 'No data loaded'}), 404
    return jsonify(meta)


@data_bp.route('/data')
def data_page():
    sid = request.sid  # type: ignore[attr-defined]
    dm = _dm()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', PAGINATION_PER_PAGE, type=int)
    try:
        result = dm.get_page(sid, page, per_page)
    except KeyError:
        return jsonify({'error': 'No data loaded — upload a file first.'}), 404
    return jsonify(result)


@data_bp.route('/data/search')
def data_search():
    sid = request.sid  # type: ignore[attr-defined]
    dm = _dm()
    q = request.args.get('q', '')
    if not q:
        return jsonify([])
    try:
        results = dm.search(sid, q)
    except KeyError:
        return jsonify({'error': 'No data loaded'}), 404
    return jsonify(results)


@data_bp.route('/data/sort', methods=['POST'])
def data_sort():
    sid = request.sid  # type: ignore[attr-defined]
    dm = _dm()
    body = request.get_json(silent=True) or {}
    by = body.get('by', '')
    ascending = body.get('ascending', True)
    try:
        dm.sort(sid, by, ascending)
    except KeyError:
        return jsonify({'error': 'No data loaded'}), 404
    return jsonify({'ok': True})


@data_bp.route('/data/edit', methods=['POST'])
def data_edit():
    sid = request.sid  # type: ignore[attr-defined]
    dm = _dm()
    body = request.get_json(silent=True) or {}
    row = body.get('row')
    col = body.get('col')
    value = body.get('value')
    if row is None or col is None:
        return jsonify({'error': 'Missing row or col'}), 400
    try:
        dm.edit_cell(sid, int(row), col, value)
    except KeyError:
        return jsonify({'error': 'No data loaded'}), 404
    return jsonify({'ok': True})


@data_bp.route('/data/add', methods=['POST'])
def data_add():
    sid = request.sid  # type: ignore[attr-defined]
    dm = _dm()
    body = request.get_json(silent=True) or {}
    add_type = body.get('type')
    position = body.get('position')
    try:
        if add_type == 'row':
            dm.add_row(sid, position)
        elif add_type == 'column':
            name = body.get('name', 'new_col')
            dm.add_column(sid, name, position)
        else:
            return jsonify({'error': 'type must be "row" or "column"'}), 400
    except KeyError:
        return jsonify({'error': 'No data loaded'}), 404
    return jsonify({'ok': True})


@data_bp.route('/data/delete', methods=['POST'])
def data_delete():
    sid = request.sid  # type: ignore[attr-defined]
    dm = _dm()
    body = request.get_json(silent=True) or {}
    del_type = body.get('type')
    indices = body.get('indices', [])
    try:
        if del_type == 'row':
            dm.delete_rows(sid, [int(i) for i in indices])
        elif del_type == 'column':
            dm.delete_columns(sid, indices)
        else:
            return jsonify({'error': 'type must be "row" or "column"'}), 400
    except KeyError:
        return jsonify({'error': 'No data loaded'}), 404
    return jsonify({'ok': True})


@data_bp.route('/data/load_path', methods=['POST'])
def data_load_path():
    """Re-load a specific dataset path (for hierarchical formats) or table (for SQLite)."""
    sid = request.sid  # type: ignore[attr-defined]
    dm = _dm()
    body = request.get_json(silent=True) or {}
    path = body.get('path')
    table_name = body.get('table_name')
    if not dm.has_session(sid):
        return jsonify({'error': 'No data loaded'}), 404
    sess = dm.sessions[sid]
    fmt = sess['format']
    filepath = sess['filepath']
    filename = sess['filename']
    kwargs = {}
    if path:
        kwargs['path'] = path
    if table_name:
        kwargs['table_name'] = table_name
    try:
        dm.load_file(sid, filepath, filename, fmt, mode='full', **kwargs)
    except Exception as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({'ok': True})
