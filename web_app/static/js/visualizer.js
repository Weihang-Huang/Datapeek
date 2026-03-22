/* DataPeek — Visualizer page logic */
(function () {
    /* ── state ──────────────────────────────────── */
    let hot = null;          // Handsontable instance
    let meta = null;         // metadata from /metadata
    let currentPage = 1;
    let totalPages = 1;
    let columns = [];
    let selRange = null;     // { rowStart, rowEnd, colStart, colEnd }
    let searchDebounce = null;
    let sortCol = null;
    let sortAsc = true;

    const spinner  = document.getElementById('spinner');
    const showSpin = () => spinner.classList.add('active');
    const hideSpin = () => spinner.classList.remove('active');

    /* ── init ───────────────────────────────────── */
    async function init() {
        showSpin();
        meta = await fetchJSON('/metadata');
        if (!meta || meta.error) { window.location.href = '/'; return; }

        document.getElementById('fileName').textContent = meta.filename || '—';
        document.getElementById('fileFormat').textContent = (meta.format || '').toUpperCase();
        document.getElementById('statsText').textContent =
            (meta.shape ? meta.shape[0] : '—') + ' rows \u00D7 ' + (meta.shape ? meta.shape[1] : '—') + ' cols';

        // Hierarchical tree sidebar
        if (meta.hierarchical && meta.tree) renderTree(meta.tree);

        // SQLite table selector
        if (meta.sqlite_view && meta.tables) renderTableSelector(meta.tables, meta.active_table);

        await loadPage(1);
        hideSpin();
    }

    /* ── fetch helper ────────────────────────────── */
    async function fetchJSON(url, opts) {
        const resp = await fetch(url, opts);
        return resp.json();
    }

    /* ── Handsontable setup ──────────────────────── */
    function initHot(cols, rows) {
        const container = document.getElementById('hotContainer');
        if (hot) hot.destroy();

        hot = new Handsontable(container, {
            data: rows,
            colHeaders: cols,
            rowHeaders: true,
            width: '100%',
            height: '100%',
            stretchH: 'all',
            manualColumnResize: true,
            manualRowResize: true,
            contextMenu: {
                items: {
                    'row_above': { name: 'Add Row Above' },
                    'row_below': { name: 'Add Row Below' },
                    'col_left':  { name: 'Add Column Left' },
                    'col_right': { name: 'Add Column Right' },
                    'sep1': '---------',
                    'remove_row': { name: 'Delete Row(s)' },
                    'remove_col': { name: 'Delete Column(s)' },
                    'sep2': '---------',
                    'copy_csv': {
                        name: 'Copy Selection as CSV',
                        callback: copySelectionCSV,
                    },
                },
            },
            afterChange: onCellChange,
            afterSelectionEnd: onSelectionEnd,
            afterCreateRow: onCreateRow,
            afterRemoveRow: onRemoveRow,
            afterCreateCol: onCreateCol,
            afterRemoveCol: onRemoveCol,
            afterColumnSort: onColumnSort,
            licenseKey: 'non-commercial-and-evaluation',
        });

        columns = cols;
    }

    /* ── data loading ────────────────────────────── */
    async function loadPage(page) {
        showSpin();
        const data = await fetchJSON('/data?page=' + page + '&per_page=100');
        if (data.error) { hideSpin(); return; }
        currentPage = data.page;
        totalPages  = data.pages;
        updatePagination();
        initHot(data.columns, data.rows);
        hideSpin();
    }

    function updatePagination() {
        document.getElementById('pageInfo').textContent = 'Page ' + currentPage + ' of ' + totalPages;
        document.getElementById('prevPage').disabled = currentPage <= 1;
        document.getElementById('nextPage').disabled = currentPage >= totalPages;
    }

    document.getElementById('prevPage').addEventListener('click', () => {
        if (currentPage > 1) loadPage(currentPage - 1);
    });
    document.getElementById('nextPage').addEventListener('click', () => {
        if (currentPage < totalPages) loadPage(currentPage + 1);
    });

    /* ── sort ─────────────────────────────────────── */
    function onColumnSort(currentSortConfig) {
        // We handle sort server-side
    }

    // Sort on column header double-click
    document.getElementById('hotContainer').addEventListener('dblclick', async (e) => {
        // Check if the click was on a header
        const th = e.target.closest('th');
        if (!th || !hot) return;
        const col = hot.toPhysicalColumn(th.cellIndex - 1);  // -1 for row header
        if (col < 0 || col >= columns.length) return;
        const colName = columns[col];

        if (sortCol === colName) {
            sortAsc = !sortAsc;
        } else {
            sortCol = colName;
            sortAsc = true;
        }

        showSpin();
        await fetch('/data/sort', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ by: colName, ascending: sortAsc }),
        });
        await loadPage(1);
        hideSpin();
    });

    /* ── search ──────────────────────────────────── */
    document.getElementById('searchInput').addEventListener('input', (e) => {
        clearTimeout(searchDebounce);
        searchDebounce = setTimeout(() => doSearch(e.target.value), 300);
    });

    async function doSearch(q) {
        if (!q.trim()) {
            // Clear highlights
            if (hot) hot.render();
            return;
        }
        const results = await fetchJSON('/data/search?q=' + encodeURIComponent(q));
        if (!hot || !Array.isArray(results)) return;

        // Highlight matching cells
        const matchSet = new Set();
        results.forEach(r => matchSet.add(r.row + ':' + r.col));

        hot.updateSettings({
            cells: function (row, col) {
                const props = {};
                const absRow = (currentPage - 1) * 100 + row;
                if (matchSet.has(absRow + ':' + col)) {
                    props.renderer = function (instance, td, row, col, prop, value) {
                        Handsontable.renderers.TextRenderer.apply(this, arguments);
                        td.style.background = 'rgba(255,200,50,.35)';
                    };
                }
                return props;
            },
        });
        hot.render();
    }

    /* ── edit cell ────────────────────────────────── */
    async function onCellChange(changes, source) {
        if (!changes || source === 'loadData') return;
        for (const [row, prop, oldVal, newVal] of changes) {
            if (oldVal === newVal) continue;
            const colIdx = typeof prop === 'number' ? prop : columns.indexOf(prop);
            const colName = columns[colIdx] || prop;
            const absRow = (currentPage - 1) * 100 + row;
            await fetch('/data/edit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ row: absRow, col: colName, value: newVal }),
            });
        }
    }

    /* ── selection tracking ───────────────────────── */
    function onSelectionEnd(r, c, r2, c2) {
        const offset = (currentPage - 1) * 100;
        selRange = {
            rowStart: offset + Math.min(r, r2),
            rowEnd:   offset + Math.max(r, r2) + 1,
            colStart: Math.min(c, c2),
            colEnd:   Math.max(c, c2) + 1,
        };
    }

    /* ── context menu actions (server-side sync) ──── */
    async function onCreateRow(index, amount) {
        const absRow = (currentPage - 1) * 100 + index;
        await fetch('/data/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: 'row', position: absRow }),
        });
        await refreshMeta();
    }

    async function onRemoveRow(index, amount) {
        const absRow = (currentPage - 1) * 100 + index;
        const indices = [];
        for (let i = 0; i < amount; i++) indices.push(absRow + i);
        await fetch('/data/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: 'row', indices }),
        });
        await refreshMeta();
    }

    async function onCreateCol(index) {
        const name = prompt('Column name:', 'new_col');
        if (!name) return;
        await fetch('/data/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: 'column', name, position: index }),
        });
        await loadPage(currentPage);
        await refreshMeta();
    }

    async function onRemoveCol(index, amount) {
        const toDelete = [];
        for (let i = 0; i < amount; i++) {
            if (columns[index + i]) toDelete.push(columns[index + i]);
        }
        await fetch('/data/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: 'column', indices: toDelete }),
        });
        await loadPage(currentPage);
        await refreshMeta();
    }

    async function refreshMeta() {
        meta = await fetchJSON('/metadata');
        if (meta && meta.shape) {
            document.getElementById('statsText').textContent =
                meta.shape[0] + ' rows \u00D7 ' + meta.shape[1] + ' cols';
        }
    }

    /* ── copy selection as CSV ────────────────────── */
    async function copySelectionCSV() {
        if (!selRange) { alert('No selection'); return; }
        const resp = await fetchJSON('/copy', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(selRange),
        });
        if (resp.csv_text) {
            await navigator.clipboard.writeText(resp.csv_text);
        }
    }

    /* ── hierarchical tree sidebar ────────────────── */
    function renderTree(tree) {
        const sidebar = document.getElementById('treeSidebar');
        sidebar.classList.add('active');
        sidebar.innerHTML = buildTreeHTML(tree);
        sidebar.addEventListener('click', async (e) => {
            const node = e.target.closest('[data-path]');
            if (!node || node.dataset.type !== 'dataset') return;
            sidebar.querySelectorAll('li').forEach(l => l.classList.remove('selected'));
            node.classList.add('selected');
            showSpin();
            await fetch('/data/load_path', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: node.dataset.path }),
            });
            meta = await fetchJSON('/metadata');
            await loadPage(1);
            if (meta && meta.shape) {
                document.getElementById('statsText').textContent =
                    meta.shape[0] + ' rows \u00D7 ' + meta.shape[1] + ' cols';
            }
            hideSpin();
        });
    }

    function buildTreeHTML(nodes) {
        let html = '<ul>';
        for (const n of nodes) {
            const icon = n.type === 'group' ? '&#128193;' : '&#128196;';
            const info = n.shape ? ' <small>(' + n.shape.join('\u00D7') + ')</small>' : '';
            html += '<li data-path="' + (n.path || n.name) + '" data-type="' + n.type + '">';
            html += '<span class="tree-icon">' + icon + '</span> ' + n.name + info;
            if (n.children && n.children.length) html += buildTreeHTML(n.children);
            html += '</li>';
        }
        html += '</ul>';
        return html;
    }

    /* ── SQLite table selector ────────────────────── */
    function renderTableSelector(tables, active) {
        const wrap = document.getElementById('tableSelector');
        const sel  = document.getElementById('tableSelect');
        wrap.classList.add('active');
        sel.innerHTML = tables.map(t =>
            '<option value="' + t + '"' + (t === active ? ' selected' : '') + '>' + t + '</option>'
        ).join('');
        sel.addEventListener('change', async () => {
            showSpin();
            await fetch('/data/load_path', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ table_name: sel.value }),
            });
            meta = await fetchJSON('/metadata');
            await loadPage(1);
            if (meta && meta.shape) {
                document.getElementById('statsText').textContent =
                    meta.shape[0] + ' rows \u00D7 ' + meta.shape[1] + ' cols';
            }
            hideSpin();
        });
    }

    /* ── navigation buttons ──────────────────────── */
    document.getElementById('closeBtn').addEventListener('click', async () => {
        await fetch('/reset', { method: 'POST' });
        window.location.href = '/';
    });
    document.getElementById('newUploadBtn').addEventListener('click', async () => {
        await fetch('/reset', { method: 'POST' });
        window.location.href = '/';
    });

    /* ── keyboard shortcuts ──────────────────────── */
    document.addEventListener('keydown', (e) => {
        if (e.ctrlKey || e.metaKey) {
            if (e.key === 'f' || e.key === 'F') {
                e.preventDefault();
                document.getElementById('searchInput').focus();
            } else if (e.key === 'c' || e.key === 'C') {
                if (selRange) { e.preventDefault(); copySelectionCSV(); }
            } else if (e.key === 's' || e.key === 'S') {
                e.preventDefault();
                document.getElementById('exportBtn').click();
            }
        }
        if (e.key === 'Delete' && selRange && hot) {
            if (confirm('Delete selected rows?')) {
                const indices = [];
                for (let i = selRange.rowStart; i < selRange.rowEnd; i++) indices.push(i);
                fetch('/data/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ type: 'row', indices }),
                }).then(() => { loadPage(currentPage); refreshMeta(); });
            }
        }
    });

    /* ── expose selRange for export.js ────────────── */
    window.DataPeek = { getSelRange: () => selRange };

    init();
})();
