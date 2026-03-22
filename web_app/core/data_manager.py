"""DataManager — in-memory session-based data store for DataPeek."""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

from web_app.config import PAGINATION_PER_PAGE
from web_app.core.readers import get_reader


class DataManager:
    """Manages one DataFrame per session, with pagination, search, sort,
    edit, add/delete operations — all in-memory, zero persistence."""

    def __init__(self):
        self.sessions: dict[str, dict] = {}

    # ── load / purge ─────────────────────────────────────────────────

    def load_file(
        self,
        session_id: str,
        filepath: str,
        filename: str,
        format_name: str,
        mode: str = 'full',
        n_rows: int | None = None,
        **kwargs,
    ) -> dict:
        """Load a file into the session.  Purges any existing data first."""
        self.purge(session_id)
        reader = get_reader(format_name)

        if mode == 'preview' and n_rows:
            df, meta = reader.read_preview(filepath, format_name=format_name, n_rows=n_rows, **kwargs)
        else:
            df, meta = reader.read_full(filepath, format_name=format_name, **kwargs)

        self.sessions[session_id] = {
            'df': df,
            'metadata': meta,
            'filename': filename,
            'format': format_name,
            'filepath': filepath,
        }
        return meta

    def purge(self, session_id: str) -> None:
        """Delete all session data from memory."""
        self.sessions.pop(session_id, None)

    # ── pagination ───────────────────────────────────────────────────

    def get_page(self, session_id: str, page: int = 1, per_page: int = PAGINATION_PER_PAGE) -> dict:
        sess = self._require(session_id)
        df: pd.DataFrame = sess['df']
        total = len(df)
        pages = max(1, math.ceil(total / per_page))
        page = max(1, min(page, pages))
        start = (page - 1) * per_page
        end = start + per_page
        chunk = df.iloc[start:end]
        return {
            'columns': list(df.columns),
            'rows': chunk.fillna('').values.tolist(),
            'total': total,
            'page': page,
            'pages': pages,
            'per_page': per_page,
        }

    # ── search ───────────────────────────────────────────────────────

    def search(self, session_id: str, query: str) -> list[dict]:
        sess = self._require(session_id)
        df: pd.DataFrame = sess['df']
        results = []
        q = query.lower()
        for row_idx in range(len(df)):
            for col_idx, col_name in enumerate(df.columns):
                cell = str(df.iat[row_idx, col_idx]).lower()
                if q in cell:
                    results.append({
                        'row': row_idx,
                        'col': col_idx,
                        'col_name': col_name,
                        'value': str(df.iat[row_idx, col_idx]),
                    })
        return results

    # ── sort ─────────────────────────────────────────────────────────

    def sort(self, session_id: str, by: str, ascending: bool = True) -> None:
        sess = self._require(session_id)
        df: pd.DataFrame = sess['df']
        if by in df.columns:
            sess['df'] = df.sort_values(by=by, ascending=ascending).reset_index(drop=True)
        elif by == '__row__':
            # sort by row (transpose, sort, transpose back)
            sess['df'] = df.T.sort_index(ascending=ascending).T

    # ── edit ─────────────────────────────────────────────────────────

    def edit_cell(self, session_id: str, row: int, col: str, value: Any) -> None:
        sess = self._require(session_id)
        df: pd.DataFrame = sess['df']
        if col in df.columns and 0 <= row < len(df):
            df.at[row, col] = value

    # ── add row / column ─────────────────────────────────────────────

    def add_row(self, session_id: str, position: int | None = None) -> None:
        sess = self._require(session_id)
        df: pd.DataFrame = sess['df']
        new_row = pd.DataFrame([{col: '' for col in df.columns}])
        if position is None or position >= len(df):
            sess['df'] = pd.concat([df, new_row], ignore_index=True)
        else:
            top = df.iloc[:position]
            bottom = df.iloc[position:]
            sess['df'] = pd.concat([top, new_row, bottom], ignore_index=True)

    def add_column(self, session_id: str, col_name: str, position: int | None = None, default=None) -> None:
        sess = self._require(session_id)
        df: pd.DataFrame = sess['df']
        if col_name in df.columns:
            col_name = f'{col_name}_1'
        if position is None or position >= len(df.columns):
            df[col_name] = default if default is not None else ''
        else:
            df.insert(position, col_name, default if default is not None else '')
        sess['df'] = df

    # ── delete rows / columns ────────────────────────────────────────

    def delete_rows(self, session_id: str, row_indices: list[int]) -> None:
        sess = self._require(session_id)
        df: pd.DataFrame = sess['df']
        sess['df'] = df.drop(index=[i for i in row_indices if 0 <= i < len(df)]).reset_index(drop=True)

    def delete_columns(self, session_id: str, col_names: list[str]) -> None:
        sess = self._require(session_id)
        df: pd.DataFrame = sess['df']
        existing = [c for c in col_names if c in df.columns]
        if existing:
            sess['df'] = df.drop(columns=existing)

    # ── selection ────────────────────────────────────────────────────

    def get_selection(self, session_id: str, row_start: int, row_end: int,
                      col_start: int, col_end: int) -> pd.DataFrame:
        sess = self._require(session_id)
        df: pd.DataFrame = sess['df']
        return df.iloc[row_start:row_end, col_start:col_end]

    # ── metadata ─────────────────────────────────────────────────────

    def get_metadata(self, session_id: str) -> dict | None:
        sess = self.sessions.get(session_id)
        if not sess:
            return None
        df: pd.DataFrame = sess['df']
        meta = dict(sess['metadata'])
        meta['filename'] = sess['filename']
        meta['format'] = sess['format']
        meta['shape'] = list(df.shape)
        meta['columns'] = list(df.columns)
        meta['dtypes'] = {col: str(dtype) for col, dtype in df.dtypes.items()}
        return meta

    # ── helpers ──────────────────────────────────────────────────────

    def _require(self, session_id: str) -> dict:
        sess = self.sessions.get(session_id)
        if not sess:
            raise KeyError(f'Session {session_id!r} not found or expired')
        return sess

    def has_session(self, session_id: str) -> bool:
        return session_id in self.sessions
