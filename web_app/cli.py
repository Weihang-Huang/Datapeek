"""CLI entry point: `datapeek [filename]` starts Flask and optionally pre-loads a file."""

import os
import sys
import webbrowser
import threading


def main():
    from web_app.app import create_app, sessions, data_manager
    from web_app.core.format_detector import detect_format
    from web_app.utils import generate_session_id

    app = create_app()
    port = int(os.environ.get('DATAPEEK_PORT', 5000))
    host = os.environ.get('DATAPEEK_HOST', '127.0.0.1')

    # If a filename was provided, pre-load it
    preload_file = None
    if len(sys.argv) > 1:
        preload_file = sys.argv[1]
        if not os.path.isfile(preload_file):
            print(f"Error: file not found: {preload_file}")
            sys.exit(1)

    def open_browser():
        url = f'http://{host}:{port}'
        if preload_file:
            url += '/view'
        webbrowser.open(url)

    if preload_file:
        # Pre-load into a default session
        with open(preload_file, 'rb') as f:
            file_bytes = f.read()
        filename = os.path.basename(preload_file)
        fmt = detect_format(filename, file_bytes)
        if fmt is None:
            print(f"Error: unsupported format: {filename}")
            sys.exit(1)
        sid = generate_session_id()
        # Use the app-level sessions dict
        app.sessions[sid] = {}  # type: ignore[attr-defined]
        app.data_manager.load_file(  # type: ignore[attr-defined]
            sid, os.path.abspath(preload_file), filename, fmt, mode='full'
        )
        app.config['PRELOAD_SID'] = sid

    threading.Timer(1.5, open_browser).start()
    print(f"DataPeek running at http://{host}:{port}")
    app.run(host=host, port=port, debug=False)


if __name__ == '__main__':
    main()
