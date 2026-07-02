from functools import wraps

from flask import current_app, redirect, session, url_for


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "token" not in session:
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped


def current_token() -> str | None:
    return session.get("token")


def current_rol() -> str | None:
    return session.get("rol")


def api_base_url() -> str:
    return current_app.config["COFFEE_API_URL"]
