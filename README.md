# StudentSpace - Student Management System

A small, responsive Flask web app for managing student records, backed by SQLite. It was written to show clean Python web code: an application factory, validated input, parameterised SQL, CSRF protection and a pytest suite.

## Features

- Create, view, edit and delete student records (ID, name, department, year, CGPA)
- Dashboard cards: total students, average CGPA, department count, highest CGPA
- Search by name or student ID, and sort by any column (ascending/descending)
- Server-side validation with clear flash messages (ranges, lengths, duplicate IDs)
- Delete confirmation dialog; deletes are POST-only
- Responsive dark UI built with Bootstrap 5

## Security notes

- All SQL uses bound parameters; the `ORDER BY` column and direction come from a whitelist
- `LIKE` wildcards in search text are escaped
- Jinja2 auto-escaping prevents XSS
- CSRF token required on every POST
- `SECRET_KEY` is read from the environment (random per process if unset); debug mode is off unless `FLASK_DEBUG=1`
- Database errors are logged, never shown to users

## Tech stack

Python 3, Flask, SQLite (`sqlite3`), Jinja2, Bootstrap 5, pytest

## Live demo

Live demo: (link added after first deploy)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/MAHESH21723/Student-Management-System)

To host your own copy for free:

1. Sign in to [Render](https://render.com) with GitHub.
2. Click the **Deploy to Render** button above.
3. Review the blueprint (`render.yaml`) and click **Apply**.

Free-plan notes: the service sleeps after about 15 minutes idle, so the first request after a pause takes about a minute. The filesystem is ephemeral, so data (including the demo students) resets on every restart or redeploy. The demo sets `DEMO_DATA=1`, which shows a "public demo" banner. The app never needs a server or domain of your own, and local use is unchanged (see Setup below).
## Setup

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate      macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env     # optional: set SECRET_KEY etc.
python app.py
```

Open http://127.0.0.1:5000. The SQLite database (`students.db`) is created automatically on first start.

## Running tests

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

Tests use a temporary database, so your real data is never touched.

## Project structure

```text
app.py                 Application factory, validation, routes, CSRF
templates/             Jinja2 templates (base, dashboard, add/edit form, error)
static/css/style.css   Theme styles
tests/                 pytest suite (validation, routes, security)
.env.example           Configuration template (copy to .env)
requirements*.txt      Pinned dependencies
```

## Configuration

| Variable | Purpose | Default |
| --- | --- | --- |
| `SECRET_KEY` | Signs sessions and CSRF tokens | random per start |
| `DATABASE_PATH` | SQLite file location | `./students.db` |
| `PORT` | Local port | `5000` |
| `FLASK_DEBUG` | `1` enables debugger/reloader | off |

## Author

Maheshwaran - [@MAHESH21723](https://github.com/MAHESH21723) - kmaheshwaran9965@gmail.com

## License

MIT - see [LICENSE](LICENSE).
