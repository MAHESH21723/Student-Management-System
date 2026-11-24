import pytest

from app import escape_like, validate_student
from conftest import rows


# ---- validation unit tests -------------------------------------------------
def form(**kw):
    base = {"id": "5", "name": "Bob", "department": "ECE", "year": "1", "cgpa": "7"}
    base.update(kw)
    return base


def test_validate_ok():
    r = validate_student(form())
    assert r.is_valid and (r.id, r.year, r.cgpa) == (5, 1, 7.0)


@pytest.mark.parametrize(
    "override",
    [
        {"id": ""}, {"id": "abc"}, {"id": "0"}, {"id": "-3"},
        {"name": "  "}, {"name": "x" * 101},
        {"department": ""},
        {"year": "0"}, {"year": "5"}, {"year": "x"}, {"year": ""},
        {"cgpa": "10.1"}, {"cgpa": "-1"}, {"cgpa": "nan"}, {"cgpa": "abc"}, {"cgpa": ""},
    ],
)
def test_validate_rejects(override):
    assert not validate_student(form(**override)).is_valid


def test_escape_like():
    assert escape_like("50%_a\\") == "50\\%\\_a\\\\"


# ---- routes ----------------------------------------------------------------
def test_index_empty(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"No student records found" in r.data


def test_db_created_on_startup(app):
    assert rows(app) == []


def test_add_student(app, client, add):
    r = add()
    assert r.status_code == 302
    assert rows(app)[0]["name"] == "Alice"
    assert b"Alice" in client.get("/").data


def test_add_duplicate_id(app, add):
    add()
    r = add(name="Other")
    assert r.status_code == 400
    assert b"already exists" in r.data
    assert len(rows(app)) == 1


def test_add_invalid_rerenders_form(app, add):
    r = add(cgpa="99", name="Keep")
    assert r.status_code == 400
    assert b"CGPA must be between 0 and 10" in r.data
    assert b'value="Keep"' in r.data
    assert rows(app) == []


def test_edit_student(app, client, add, token):
    add()
    assert client.get("/edit/1").status_code == 200
    r = client.post("/edit/1", data={"_csrf": token, "name": "Alicia",
                                      "department": "IT", "year": "3", "cgpa": "9"})
    assert r.status_code == 302
    assert rows(app)[0] | {} == {"id": 1, "name": "Alicia", "department": "IT",
                                  "year": 3, "cgpa": 9.0}


def test_edit_invalid_keeps_row(app, client, add, token):
    add()
    r = client.post("/edit/1", data={"_csrf": token, "name": "", "department": "IT",
                                      "year": "3", "cgpa": "9"})
    assert r.status_code == 400
    assert rows(app)[0]["name"] == "Alice"


def test_edit_missing_redirects(client):
    assert client.get("/edit/999").status_code == 302


def test_delete_student(app, client, add, token):
    add()
    r = client.post("/delete/1", data={"_csrf": token})
    assert r.status_code == 302
    assert rows(app) == []


def test_delete_get_not_allowed(client):
    assert client.get("/delete/1").status_code == 405


def test_search_by_name_and_id(client, add):
    add(id="1", name="Alice")
    add(id="22", name="Bob")
    body = client.get("/?search=ali").get_data(as_text=True)
    assert "Alice" in body and "Bob" not in body
    body = client.get("/?search=22").get_data(as_text=True)
    assert "Bob" in body and "Alice" not in body


def test_search_wildcards_are_literal(client, add):
    add(id="1", name="Alice")
    assert "Alice" not in client.get("/?search=%25").get_data(as_text=True)


def test_sorting(client, add):
    add(id="1", name="Zed", cgpa="5")
    add(id="2", name="Amy", cgpa="9")
    body = client.get("/?sort=name&direction=asc").get_data(as_text=True)
    assert body.index("Amy") < body.index("Zed")
    body = client.get("/?sort=cgpa&direction=desc").get_data(as_text=True)
    assert body.index("Amy") < body.index("Zed")


def test_sort_injection_is_ignored(client, add):
    add()
    r = client.get("/?sort=id;DROP TABLE students&direction=asc;--")
    assert r.status_code == 200
    assert b"Alice" in r.data


def test_search_sql_injection_is_inert(app, client, add):
    add()
    r = client.get("/?search=' OR 1=1; DROP TABLE students;--")
    assert r.status_code == 200
    assert len(rows(app)) == 1


def test_xss_is_escaped(client, add):
    add(name="<script>alert(1)</script>")
    body = client.get("/").get_data(as_text=True)
    assert "<script>alert(1)</script>" not in body
    assert "&lt;script&gt;" in body


def test_stats(client, add):
    add(id="1", cgpa="8", department="A")
    add(id="2", cgpa="9", department="B")
    body = client.get("/").get_data(as_text=True)
    assert "8.5" in body and "9.0" in body


# ---- CSRF / errors ---------------------------------------------------------
def test_post_without_csrf_rejected(app, client):
    r = client.post("/add", data=form())
    assert r.status_code == 400
    assert rows(app) == []


def test_delete_without_csrf_rejected(app, client, add):
    add()
    assert client.post("/delete/1").status_code == 400
    assert len(rows(app)) == 1


def test_404_page(client):
    r = client.get("/nope")
    assert r.status_code == 404
    assert b"404" in r.data


def test_debug_off_and_secret_not_hardcoded(app):
    assert not app.debug
    assert app.config["SECRET_KEY"] != "super_secret_key_for_portfolio"
