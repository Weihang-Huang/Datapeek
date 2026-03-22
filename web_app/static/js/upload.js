/* DataPeek — Upload page logic */
(function () {
    const dropzone   = document.getElementById('dropzone');
    const fileInput  = document.getElementById('fileInput');
    const fileInfo   = document.getElementById('fileInfo');
    const errorMsg   = document.getElementById('errorMsg');
    const uploadBtn  = document.getElementById('uploadBtn');
    const sizeModal  = document.getElementById('sizeModal');
    const sizeText   = document.getElementById('sizeText');
    const previewWrap = document.getElementById('previewRowsWrap');
    const previewRows = document.getElementById('previewRows');
    const modalCancel = document.getElementById('modalCancel');
    const modalContinue = document.getElementById('modalContinue');

    const ALLOWED = new Set([
        '.parquet','.pq','.feather','.arrow','.ipc','.orc','.avro',
        '.h5','.hdf5','.he5','.nc','.nc4','.netcdf','.zarr','.zip',
        '.pkl','.pickle','.msgpack','.npy','.npz',
        '.pt','.pth','.safetensors',
        '.db','.sqlite','.sqlite3','.mdb','.lmdb'
    ]);

    let selectedFile = null;

    /* ── helpers ──────────────────────────────────── */
    function showError(msg) {
        errorMsg.textContent = msg;
        errorMsg.classList.add('visible');
    }
    function clearError() {
        errorMsg.textContent = '';
        errorMsg.classList.remove('visible');
    }
    function humanSize(bytes) {
        const units = ['B','KB','MB','GB'];
        let i = 0;
        let v = bytes;
        while (v >= 1024 && i < units.length - 1) { v /= 1024; i++; }
        return v.toFixed(1) + ' ' + units[i];
    }
    function extOf(name) {
        const dot = name.lastIndexOf('.');
        return dot >= 0 ? name.slice(dot).toLowerCase() : '';
    }

    /* ── drag & drop ─────────────────────────────── */
    dropzone.addEventListener('click', () => fileInput.click());
    dropzone.addEventListener('dragover', e => { e.preventDefault(); dropzone.classList.add('drag-over'); });
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag-over'));
    dropzone.addEventListener('drop', e => {
        e.preventDefault();
        dropzone.classList.remove('drag-over');
        if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
    });
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length) handleFile(fileInput.files[0]);
    });

    function handleFile(file) {
        clearError();
        const ext = extOf(file.name);
        if (!ALLOWED.has(ext)) {
            showError('Unsupported file type: ' + ext);
            selectedFile = null;
            uploadBtn.disabled = true;
            fileInfo.classList.remove('visible');
            return;
        }
        selectedFile = file;
        fileInfo.innerHTML = '<strong>' + file.name + '</strong> &mdash; ' + humanSize(file.size);
        fileInfo.classList.add('visible');
        uploadBtn.disabled = false;
    }

    /* ── upload ───────────────────────────────────── */
    uploadBtn.addEventListener('click', async () => {
        if (!selectedFile) return;
        clearError();
        uploadBtn.disabled = true;
        uploadBtn.textContent = 'Uploading…';

        const fd = new FormData();
        fd.append('file', selectedFile);

        try {
            const resp = await fetch('/upload', { method: 'POST', body: fd });
            const data = await resp.json();
            if (data.error) {
                showError(data.error);
                uploadBtn.disabled = false;
                uploadBtn.textContent = 'Upload';
                return;
            }
            if (data.prompt) {
                sizeText.textContent = 'This file is ' + data.size + ' (' + data.format + ' format).';
                sizeModal.classList.add('active');
                uploadBtn.disabled = false;
                uploadBtn.textContent = 'Upload';
                return;
            }
            if (data.redirect) {
                window.location.href = data.redirect;
            }
        } catch (err) {
            showError('Upload failed: ' + err.message);
            uploadBtn.disabled = false;
            uploadBtn.textContent = 'Upload';
        }
    });

    /* ── modal logic ─────────────────────────────── */
    document.querySelectorAll('input[name="loadMode"]').forEach(r => {
        r.addEventListener('change', () => {
            previewWrap.style.display = r.value === 'preview' && r.checked ? 'block' : 'none';
        });
    });
    modalCancel.addEventListener('click', () => sizeModal.classList.remove('active'));
    modalContinue.addEventListener('click', async () => {
        const mode = document.querySelector('input[name="loadMode"]:checked').value;
        const rows = parseInt(previewRows.value, 10) || 1000;
        sizeModal.classList.remove('active');
        uploadBtn.disabled = true;
        uploadBtn.textContent = 'Loading…';

        try {
            const resp = await fetch('/upload/confirm', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mode, n_rows: rows }),
            });
            const data = await resp.json();
            if (data.error) {
                showError(data.error);
            } else if (data.redirect) {
                window.location.href = data.redirect;
            }
        } catch (err) {
            showError('Load failed: ' + err.message);
        }
        uploadBtn.disabled = false;
        uploadBtn.textContent = 'Upload';
    });
})();
