import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app, get_db  # noqa: E402


@pytest.fixture()
def app(tmp_path):
    return create_app(
        {"TESTING": True, "SECRET_KEY": "test", "DATABASE": str(tmp_path / "test.db")}
    )


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def token(client):
    """Fetch a page to establish a session and return its CSRF token."""
    html = client.get("/add").get_data(as_text=True)
    return re.search(r'name="_csrf" value="([^"]+)"', html).group(1)


@pytest.fixture()
def add(client, token):
    """Helper that POSTs a new student with a valid CSRF token."""

    def _add(**overrides):
        data = {"_csrf": token, "id": "1", "name": "Alice", "department": "CSE",
                "year": "2", "cgpa": "8.5"}
        data.update(overrides)
        return client.post("/add", data=data)

    return _add


def rows(app):
    with app.app_context():
        return [dict(r) for r in get_db().execute("SELECT * FROM students ORDER BY id")]
