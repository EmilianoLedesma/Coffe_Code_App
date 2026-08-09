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
    from app.blueprints.usuarios import bp as usuarios_bp
    from app.blueprints.productos import bp as productos_bp
    from app.blueprints.categorias import bp as categorias_bp
    from app.blueprints.ingredientes import bp as ingredientes_bp
    from app.blueprints.recetas import bp as recetas_bp
    from app.blueprints.reportes import bp as reportes_bp
    from app.blueprints.cortes_diarios import bp as cortes_diarios_bp
    from app.blueprints.gastos_fijos import bp as gastos_fijos_bp
    from app.blueprints.tickets import bp as tickets_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(productos_bp)
    app.register_blueprint(categorias_bp)
    app.register_blueprint(ingredientes_bp)
    app.register_blueprint(recetas_bp)
    app.register_blueprint(reportes_bp)
    app.register_blueprint(cortes_diarios_bp)
    app.register_blueprint(gastos_fijos_bp)
    app.register_blueprint(tickets_bp)

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
        return render_template("errors/api_error.html", mensaje=error.detail), error.status_code or 500

    return app
