from flask import Blueprint

from app.auth import login_required

bp = Blueprint("dashboard", __name__)


@bp.route("/")
@login_required
def index():
    return "Dashboard (placeholder — se implementa en Task 11)"
