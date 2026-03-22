/* DataPeek — Export dropdown logic */
(function () {
    const exportBtn  = document.getElementById('exportBtn');
    const exportMenu = document.getElementById('exportMenu');

    // Toggle dropdown
    exportBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        exportMenu.classList.toggle('open');
    });
    document.addEventListener('click', () => exportMenu.classList.remove('open'));
    exportMenu.addEventListener('click', (e) => e.stopPropagation());

    // Export items
    exportMenu.querySelectorAll('.item[data-fmt]').forEach(item => {
        item.addEventListener('click', () => {
            const fmt = item.dataset.fmt;
            const scope = document.querySelector('input[name="exportScope"]:checked').value;
            exportMenu.classList.remove('open');

            if (scope === 'full') {
                // Trigger download via hidden anchor
                const a = document.createElement('a');
                a.href = '/export/full?fmt=' + encodeURIComponent(fmt);
                a.download = '';
                document.body.appendChild(a);
                a.click();
                a.remove();
            } else {
                const sel = window.DataPeek ? window.DataPeek.getSelRange() : null;
                if (!sel) {
                    alert('No selection — please select cells first.');
                    return;
                }
                // POST selection export and trigger download
                fetch('/export/selection', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        fmt,
                        row_start: sel.rowStart,
                        row_end:   sel.rowEnd,
                        col_start: sel.colStart,
                        col_end:   sel.colEnd,
                    }),
                })
                .then(resp => resp.blob())
                .then(blob => {
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'selection.' + fmt;
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                    URL.revokeObjectURL(url);
                });
            }
        });
    });
})();
