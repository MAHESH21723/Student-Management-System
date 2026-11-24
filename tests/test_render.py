"""Render / public-demo mode."""
from app import DEMO_NOTICE, create_app, get_db


def make(tmp_path, monkeypatch, **env):
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return create_app({"TESTING": True, "SECRET_KEY": "t", "DATABASE": str(tmp_path / "d.db")})


def test_render_env_sets_secure_cookies_and_proxyfix(tmp_path, monkeypatch):
    app = make(tmp_path, monkeypatch, RENDER="1")
    assert app.config["SESSION_COOKIE_SECURE"] is True
    resp = app.test_client().get("/", headers={"X-Forwarded-Proto": "https"})
    assert resp.status_code == 200


def test_demo_data_seeds_once_and_shows_banner(tmp_path, monkeypatch):
    app = make(tmp_path, monkeypatch, RENDER="1", DEMO_DATA="1")
    with app.app_context():
        count = get_db().execute("SELECT COUNT(*) FROM students").fetchone()[0]
    assert count == 8
    make(tmp_path, monkeypatch, DEMO_DATA="1")  # second start must not duplicate
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM students").fetchone()[0] == 8
    html = app.test_client().get("/").get_data(as_text=True)
    assert "DEMO-001" in html
    assert DEMO_NOTICE.replace("'", "&#39;") in html


def test_no_demo_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("DEMO_DATA", raising=False)
    monkeypatch.delenv("RENDER", raising=False)
    app = make(tmp_path, monkeypatch)
    html = app.test_client().get("/").get_data(as_text=True)
    assert "Public demo" not in html
    assert "SESSION_COOKIE_SECURE" not in app.config or not app.config["SESSION_COOKIE_SECURE"]