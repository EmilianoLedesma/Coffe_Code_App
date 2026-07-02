import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app


@pytest.fixture()
def app():
    flask_app = create_app({"TESTING": True, "COFFEE_API_URL": "http://testserver"})
    yield flask_app


@pytest.fixture()
def client(app):
    return app.test_client()
