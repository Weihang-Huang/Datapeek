"""DataPeek — Flask application factory."""

from flask import Flask, request, g

from web_app.config import MAX_CONTENT_LENGTH
from web_app.utils import generate_session_id
from web_app.core.data_manager import DataManager

# ── Canonical shared state ───────────────────────────────────────────
# These are the SINGLE authoritative instances.  Every other module
# must import from here (or, better, use the helpers below).
sessions: dict[str, dict] = {}
data_manager = DataManager()


def get_sessions() -> dict[str, dict]:
    """Return the canonical sessions dict."""
    return sessions


def get_data_manager() -> DataManager:
    """Return the canonical DataManager instance."""
    return data_manager


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        template_folder='templates',
        static_folder='static',
    )
    app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
    app.secret_key = generate_session_id()

    # Store references on the app so blueprints can always find them
    app.sessions = sessions          # type: ignore[attr-defined]
    app.data_manager = data_manager  # type: ignore[attr-defined]

    # ── before-request: ensure session cookie ────────────────────────
    @app.before_request
    def ensure_session():
        _sessions = app.sessions     # type: ignore[attr-defined]
        sid = request.cookies.get('datapeek_sid')
        if not sid or sid not in _sessions:
            sid = generate_session_id()
            _sessions[sid] = {}
        request.sid = sid            # type: ignore[attr-defined]

    @app.after_request
    def set_session_cookie(response):
        sid = getattr(request, 'sid', None)
        if sid:
            response.set_cookie('datapeek_sid', sid, httponly=True, samesite='Lax')
        return response

    # ── register blueprints ──────────────────────────────────────────
    from web_app.routes.upload import upload_bp
    from web_app.routes.data import data_bp
    from web_app.routes.export import export_bp

    app.register_blueprint(upload_bp)
    app.register_blueprint(data_bp)
    app.register_blueprint(export_bp)

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
