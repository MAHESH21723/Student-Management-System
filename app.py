import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, g

DATABASE = 'students.db'

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_portfolio'  # Necessary for flash messaging

def get_db():
    """Returns database connection from the application context g."""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    """Closes database connection at the end of the request context."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    """Initializes the database schema if it does not exist."""
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                department TEXT NOT NULL,
                year INTEGER NOT NULL,
                cgpa REAL NOT NULL
            )
        ''')
        db.commit()

@app.route('/')
def index():
    db = get_db()
    cursor = db.cursor()
    
    # Search filter parameter
    search_query = request.args.get('search', '').strip()
    
    # Sorting parameters
    sort_by = request.args.get('sort', 'id')
    direction = request.args.get('direction', 'asc')
    
    # Sanitize sort fields to prevent SQL injection in ORDER BY clause
    allowed_sort_fields = {'id', 'name', 'department', 'year', 'cgpa'}
    if sort_by not in allowed_sort_fields:
        sort_by = 'id'
    if direction not in {'asc', 'desc'}:
        direction = 'asc'
        
    # Perform parameterized query filtering if search text is provided
    if search_query:
        sql = f'''
            SELECT * FROM students 
            WHERE CAST(id AS TEXT) LIKE ? OR name LIKE ?
            ORDER BY {sort_by} {direction.upper()}
        '''
        params = (f'%{search_query}%', f'%{search_query}%')
        cursor.execute(sql, params)
    else:
        sql = f'SELECT * FROM students ORDER BY {sort_by} {direction.upper()}'
        cursor.execute(sql)
        
    students = cursor.fetchall()
    
    # Gather statistics for dashboard widget summary cards
    cursor.execute('SELECT COUNT(*) FROM students')
    total_students = cursor.fetchone()[0]
    
    cursor.execute('SELECT AVG(cgpa) FROM students')
    avg_cgpa_row = cursor.fetchone()
    avg_cgpa = round(avg_cgpa_row[0], 2) if (avg_cgpa_row and avg_cgpa_row[0] is not None) else 0.0
    
    cursor.execute('SELECT COUNT(DISTINCT department) FROM students')
    dept_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT MAX(cgpa) FROM students')
    max_cgpa_row = cursor.fetchone()
    max_cgpa = round(max_cgpa_row[0], 2) if (max_cgpa_row and max_cgpa_row[0] is not None) else 0.0
    
    return render_template(
        'index.html', 
        students=students, 
        search=search_query,
        sort_by=sort_by,
        direction=direction,
        total_students=total_students,
        avg_cgpa=avg_cgpa,
        dept_count=dept_count,
        max_cgpa=max_cgpa
    )

@app.route('/add', methods=['GET', 'POST'])
def add_student():
    if request.method == 'POST':
        student_id_str = request.form.get('id', '').strip()
        name = request.form.get('name', '').strip()
        department = request.form.get('department', '').strip()
        year_str = request.form.get('year', '').strip()
        cgpa_str = request.form.get('cgpa', '').strip()
        
        errors = []
        
        # Validations according to requirements
        if not name:
            errors.append("Name field is required.")
            
        if not student_id_str:
            errors.append("Student ID is required.")
        else:
            try:
                student_id = int(student_id_str)
                if student_id <= 0:
                    errors.append("Student ID must be a positive integer.")
            except ValueError:
                errors.append("Student ID must be a valid number.")
                
        if not year_str:
            errors.append("Year field is required.")
        else:
            try:
                year = int(year_str)
                if year < 1 or year > 4:
                    errors.append("Year must be between 1 and 4.")
            except ValueError:
                errors.append("Year must be an integer between 1 and 4.")
                
        if not cgpa_str:
            errors.append("CGPA is required.")
        else:
            try:
                cgpa = float(cgpa_str)
                if cgpa < 0.0 or cgpa > 10.0:
                    errors.append("Invalid CGPA.")
            except ValueError:
                errors.append("Invalid CGPA.")
                
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('add_student.html', form_data=request.form)
            
        db = get_db()
        cursor = db.cursor()
        
        # Ensure student ID uniqueness
        cursor.execute('SELECT id FROM students WHERE id = ?', (student_id,))
        if cursor.fetchone():
            flash("Student ID already exists.", 'danger')
            return render_template('add_student.html', form_data=request.form)
            
        try:
            cursor.execute('''
                INSERT INTO students (id, name, department, year, cgpa)
                VALUES (?, ?, ?, ?, ?)
            ''', (student_id, name, department, year, cgpa))
            db.commit()
            flash("Student added successfully.", "success")
            return redirect(url_for('index'))
        except Exception as e:
            flash(f"Database error occurred: {str(e)}", "danger")
            return render_template('add_student.html', form_data=request.form)
            
    return render_template('add_student.html', form_data={})

@app.route('/edit/<int:student_id>', methods=['GET', 'POST'])
def edit_student(student_id):
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('SELECT * FROM students WHERE id = ?', (student_id,))
    student = cursor.fetchone()
    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        department = request.form.get('department', '').strip()
        year_str = request.form.get('year', '').strip()
        cgpa_str = request.form.get('cgpa', '').strip()
        
        errors = []
        
        if not name:
            errors.append("Name field is required.")
            
        if not year_str:
            errors.append("Year field is required.")
        else:
            try:
                year = int(year_str)
                if year < 1 or year > 4:
                    errors.append("Year must be between 1 and 4.")
            except ValueError:
                errors.append("Year must be an integer between 1 and 4.")
                
        if not cgpa_str:
            errors.append("CGPA is required.")
        else:
            try:
                cgpa = float(cgpa_str)
                if cgpa < 0.0 or cgpa > 10.0:
                    errors.append("Invalid CGPA.")
            except ValueError:
                errors.append("Invalid CGPA.")
                
        if errors:
            for error in errors:
                flash(error, 'danger')
            # Mock the format of database record for re-rendering
            mock_student = {
                'id': student_id,
                'name': name,
                'department': department,
                'year': year_str,
                'cgpa': cgpa_str
            }
            return render_template('edit_student.html', student=mock_student)
            
        try:
            cursor.execute('''
                UPDATE students 
                SET name = ?, department = ?, year = ?, cgpa = ? 
                WHERE id = ?
            ''', (name, department, year, cgpa, student_id))
            db.commit()
            flash("Student information updated successfully.", "success")
            return redirect(url_for('index'))
        except Exception as e:
            flash(f"Database error occurred: {str(e)}", "danger")
            return render_template('edit_student.html', student=student)
            
    return render_template('edit_student.html', student=student)

@app.route('/delete/<int:student_id>', methods=['POST'])
def delete_student(student_id):
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute('DELETE FROM students WHERE id = ?', (student_id,))
        db.commit()
        flash("Student deleted successfully.", "success")
    except Exception as e:
        flash(f"Error deleting student: {str(e)}", "danger")
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    # Runs on default port 5000
    app.run(debug=True, port=5000)
