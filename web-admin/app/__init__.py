from datetime import timedelta

from flask import Flask, render_template

from app.api_client import ApiError
from app.config import settings


def create_app(config_overrides: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = settings.secret_key
    app.config["COFFEE_API_URL"] = settings.coffee_api_url
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=settings.session_lifetime_hours)
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    if config_overrides:
        app.config.update(config_overrides)

    from app.blueprints.auth import bp as auth_bp
    from app.blueprints.dashboard import bp as dashboard_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.errorhandler(ApiError)
    def handle_api_error(error: ApiError):
        if error.status_code == 401:
            from flask import session

            session.clear()
            return render_template("errors/401.html"), 401
        if error.status_code == 403:
            return render_template("errors/403.html"), 403
        return render_template("errors/401.html", mensaje=error.detail), error.status_code or 500

    return app
