"""StudentSpace - a small Flask + SQLite student record manager."""
from __future__ import annotations

import os
import secrets
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from dotenv import load_dotenv
from flask import (
    Flask,
    abort,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.wrappers import Response

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

SORTABLE_COLUMNS = ("id", "name", "department", "year", "cgpa")
MAX_NAME_LENGTH = 100
MAX_DEPARTMENT_LENGTH = 60
MAX_SEARCH_LENGTH = 100
MAX_STUDENT_ID = 2**53  # keeps ids safe for JSON/JS consumers

DEMO_NOTICE = (
    "Public demo: data is shared and resets, don't enter personal information."
)

# Obviously fictional records. The id column is numeric, so the DEMO-nnn label
# is part of the name (ids 9001-9008).
DEMO_STUDENTS = [
    (9001, "DEMO-001 Test Student Alpha", "Demo Computer Science", 1, 8.1),
    (9002, "DEMO-002 Test Student Beta", "Demo Computer Science", 2, 7.4),
    (9003, "DEMO-003 Test Student Gamma", "Demo Mechanical", 3, 6.9),
    (9004, "DEMO-004 Test Student Delta", "Demo Electronics", 4, 9.2),
    (9005, "DEMO-005 Test Student Epsilon", "Demo Civil", 2, 7.8),
    (9006, "DEMO-006 Test Student Zeta", "Demo Electronics", 1, 8.6),
    (9007, "DEMO-007 Test Student Eta", "Demo Mechanical", 3, 7.1),
    (9008, "DEMO-008 Test Student Theta", "Demo Civil", 4, 8.9),
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    id         INTEGER PRIMARY KEY,
    name       TEXT    NOT NULL,
    department TEXT    NOT NULL,
    year       INTEGER NOT NULL CHECK (year BETWEEN 1 AND 4),
    cgpa       REAL    NOT NULL CHECK (cgpa BETWEEN 0 AND 10)
)
"""


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------
@dataclass
class StudentInput:
    """Result of validating a submitted student form."""

    id: int | None = None
    name: str = ""
    department: str = ""
    year: int | None = None
    cgpa: float | None = None
    errors: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors


def validate_student(form: Mapping[str, str], require_id: bool = True) -> StudentInput:
    """Validate raw form data and return typed values plus any error messages."""
    result = StudentInput()
    result.name = form.get("name", "").strip()
    result.department = form.get("department", "").strip()

    if require_id:
        raw_id = form.get("id", "").strip()
        if not raw_id:
            result.errors.append("Student ID is required.")
        else:
            try:
                result.id = int(raw_id)
            except ValueError:
                result.errors.append("Student ID must be a whole number.")
            else:
                if not 0 < result.id <= MAX_STUDENT_ID:
                    result.errors.append("Student ID must be a positive number.")

    if not result.name:
        result.errors.append("Name is required.")
    elif len(result.name) > MAX_NAME_LENGTH:
        result.errors.append(f"Name must be at most {MAX_NAME_LENGTH} characters.")

    if not result.department:
        result.errors.append("Department is required.")
    elif len(result.department) > MAX_DEPARTMENT_LENGTH:
        result.errors.append(
            f"Department must be at most {MAX_DEPARTMENT_LENGTH} characters."
        )

    raw_year = form.get("year", "").strip()
    if not raw_year:
        result.errors.append("Year is required.")
    else:
        try:
            result.year = int(raw_year)
        except ValueError:
            result.errors.append("Year must be a whole number between 1 and 4.")
        else:
            if not 1 <= result.year <= 4:
                result.errors.append("Year must be between 1 and 4.")

    raw_cgpa = form.get("cgpa", "").strip()
    if not raw_cgpa:
        result.errors.append("CGPA is required.")
    else:
        try:
            result.cgpa = float(raw_cgpa)
        except ValueError:
            result.errors.append("CGPA must be a number.")
        else:
            # "not (a <= x <= b)" also rejects NaN.
            if not 0.0 <= result.cgpa <= 10.0:
                result.errors.append("CGPA must be between 0 and 10.")

    return result


def escape_like(text: str) -> str:
    """Escape LIKE wildcards so user input is matched literally."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


# --------------------------------------------------------------------------
# Application factory
# --------------------------------------------------------------------------
def create_app(test_config: Mapping[str, Any] | None = None) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_mapping(
        # Set SECRET_KEY in the environment (see .env.example). The fallback is
        # random per process, so sessions simply reset on restart in development.
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        DATABASE=os.environ.get("DATABASE_PATH") or str(BASE_DIR / "students.db"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if os.environ.get("RENDER"):
        # Behind Render's HTTPS proxy: trust one hop of X-Forwarded-* headers.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)  # type: ignore[method-assign]
        app.config["SESSION_COOKIE_SECURE"] = True
    app.config["DEMO_DATA"] = os.environ.get("DEMO_DATA") == "1"
    if test_config:
        app.config.update(test_config)

    @app.context_processor
    def inject_demo() -> dict[str, Any]:
        return {"demo_mode": app.config["DEMO_DATA"], "demo_notice": DEMO_NOTICE}

    app.teardown_appcontext(close_db)
    init_db(app)
    if app.config["DEMO_DATA"]:
        seed_demo_data(app)
    register_csrf(app)
    register_routes(app)
    register_error_handlers(app)
    return app


def get_db() -> sqlite3.Connection:
    """Return the per-request SQLite connection."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_exc: BaseException | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app: Flask) -> None:
    """Create the database file and schema if they do not exist."""
    Path(app.config["DATABASE"]).resolve().parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(app.config["DATABASE"], timeout=30) as conn:
        conn.execute(SCHEMA)


def seed_demo_data(app: Flask) -> None:
    """Insert obviously fictional students when the table is empty (demo mode)."""
    with sqlite3.connect(app.config["DATABASE"], timeout=30) as conn:
        if conn.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 0:
            # OR IGNORE: several gunicorn workers may seed at the same time.
            conn.executemany(
                "INSERT OR IGNORE INTO students (id, name, department, year, cgpa) "
                "VALUES (?, ?, ?, ?, ?)",
                DEMO_STUDENTS,
            )


# --------------------------------------------------------------------------
# CSRF protection (session token checked on every state-changing request)
# --------------------------------------------------------------------------
def register_csrf(app: Flask) -> None:
    def csrf_token() -> str:
        if "_csrf" not in session:
            session["_csrf"] = secrets.token_hex(16)
        return session["_csrf"]

    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def check_csrf() -> None:
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            expected = session.get("_csrf")
            sent = request.form.get("_csrf", "")
            if not expected or not secrets.compare_digest(expected, sent):
                abort(400, description="Invalid or missing CSRF token.")


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------
def register_routes(app: Flask) -> None:
    @app.get("/")
    def index() -> str:
        search = request.args.get("search", "").strip()[:MAX_SEARCH_LENGTH]
        sort_by = request.args.get("sort", "id")
        direction = request.args.get("direction", "asc")
        if sort_by not in SORTABLE_COLUMNS:
            sort_by = "id"
        if direction not in ("asc", "desc"):
            direction = "asc"

        db = get_db()
        # sort_by / direction are whitelisted above, so interpolation is safe;
        # all user text goes through bound parameters.
        query = "SELECT * FROM students"
        params: tuple[str, ...] = ()
        if search:
            pattern = f"%{escape_like(search)}%"
            query += " WHERE CAST(id AS TEXT) LIKE ? ESCAPE '\\' OR name LIKE ? ESCAPE '\\'"
            params = (pattern, pattern)
        query += f" ORDER BY {sort_by} {direction.upper()}, id ASC"
        students = db.execute(query, params).fetchall()

        stats = db.execute(
            "SELECT COUNT(*) AS total, AVG(cgpa) AS avg_cgpa, "
            "COUNT(DISTINCT department) AS depts, MAX(cgpa) AS max_cgpa "
            "FROM students"
        ).fetchone()

        return render_template(
            "index.html",
            students=students,
            search=search,
            sort_by=sort_by,
            direction=direction,
            total_students=stats["total"],
            avg_cgpa=round(stats["avg_cgpa"] or 0.0, 2),
            dept_count=stats["depts"],
            max_cgpa=round(stats["max_cgpa"] or 0.0, 2),
        )

    @app.route("/add", methods=["GET", "POST"])
    def add_student() -> str | Response:
        if request.method == "POST":
            data = validate_student(request.form, require_id=True)
            if data.is_valid:
                try:
                    with get_db() as db:
                        db.execute(
                            "INSERT INTO students (id, name, department, year, cgpa) "
                            "VALUES (?, ?, ?, ?, ?)",
                            (data.id, data.name, data.department, data.year, data.cgpa),
                        )
                except sqlite3.IntegrityError:
                    data.errors.append("Student ID already exists.")
                else:
                    flash("Student added successfully.", "success")
                    return redirect(url_for("index"))
            for error in data.errors:
                flash(error, "danger")
            return render_template("add_student.html", form_data=request.form), 400
        return render_template("add_student.html", form_data={})

    @app.route("/edit/<int:student_id>", methods=["GET", "POST"])
    def edit_student(student_id: int) -> str | Response:
        db = get_db()
        student = db.execute(
            "SELECT * FROM students WHERE id = ?", (student_id,)
        ).fetchone()
        if student is None:
            flash("Student not found.", "danger")
            return redirect(url_for("index"))

        if request.method == "POST":
            data = validate_student(request.form, require_id=False)
            if data.is_valid:
                with db:
                    db.execute(
                        "UPDATE students SET name = ?, department = ?, year = ?, "
                        "cgpa = ? WHERE id = ?",
                        (data.name, data.department, data.year, data.cgpa, student_id),
                    )
                flash("Student updated successfully.", "success")
                return redirect(url_for("index"))
            for error in data.errors:
                flash(error, "danger")
            submitted = {"id": student_id, **request.form.to_dict()}
            return render_template("edit_student.html", student=submitted), 400
        return render_template("edit_student.html", student=student)

    @app.post("/delete/<int:student_id>")
    def delete_student(student_id: int) -> Response:
        with get_db() as db:
            cursor = db.execute("DELETE FROM students WHERE id = ?", (student_id,))
        if cursor.rowcount:
            flash("Student deleted successfully.", "success")
        else:
            flash("Student not found.", "danger")
        return redirect(url_for("index"))


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(400)
    @app.errorhandler(404)
    @app.errorhandler(405)
    def http_error(error: Any) -> tuple[str, int]:
        return render_template("error.html", error=error), error.code

    @app.errorhandler(sqlite3.Error)
    def database_error(_error: sqlite3.Error) -> tuple[str, int]:
        app.logger.exception("Database error")
        return render_template("error.html", error=None), 500


if __name__ == "__main__":
    # Local development only. Set FLASK_DEBUG=1 to enable the debugger/reloader.
    create_app().run(
        host="127.0.0.1",
        port=int(os.environ.get("PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
