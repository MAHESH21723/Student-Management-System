import os
import unittest
import sqlite3

# Import our Flask application module
import app

class StudentManagementSystemTestCase(unittest.TestCase):
    
    def setUp(self):
        # Override the database file path to point to a test database
        app.DATABASE = 'test_students.db'
        
        # Configure app for testing & exceptions propagation
        app.app.config['TESTING'] = True
        app.app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.app.test_client()
        
        # Initialize test database schema
        app.init_db()
        
        # Clean up database table contents just in case
        self.clear_db()

    def tearDown(self):
        # Ensure any connection in app context is cleaned up
        self.clear_db()
        
        # Delete the test database file
        if os.path.exists('test_students.db'):
            try:
                os.remove('test_students.db')
            except OSError:
                pass

    def clear_db(self):
        """Helper to truncate students table in test database."""
        with app.app.app_context():
            db = app.get_db()
            cursor = db.cursor()
            cursor.execute('DELETE FROM students')
            db.commit()

    def add_test_student(self, sid, name, dept, year, cgpa):
        """Helper to directly insert a student for setup phase."""
        with app.app.app_context():
            db = app.get_db()
            cursor = db.cursor()
            cursor.execute(
                'INSERT INTO students (id, name, department, year, cgpa) VALUES (?, ?, ?, ?, ?)',
                (sid, name, dept, year, cgpa)
            )
            db.commit()

    def test_dashboard_load(self):
        """Test that the dashboard page loads correctly and displays widgets."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'StudentSpace', response.data)
        self.assertIn(b'Total Students', response.data)
        self.assertIn(b'Average CGPA', response.data)

    def test_add_student_success(self):
        """Test successful registration of a student record."""
        data = {
            'id': '101',
            'name': 'Maheshwaran',
            'department': 'AI&DS',
            'year': '4',
            'cgpa': '8.1'
        }
        response = self.client.post('/add', data=data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Student added successfully.', response.data)
        
        # Check database directly
        with app.app.app_context():
            db = app.get_db()
            cursor = db.cursor()
            cursor.execute('SELECT * FROM students WHERE id = 101')
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row['name'], 'Maheshwaran')
            self.assertEqual(row['department'], 'AI&DS')
            self.assertEqual(row['year'], 4)
            self.assertEqual(row['cgpa'], 8.1)

    def test_add_student_duplicate_id(self):
        """Test validation preventing duplicate student IDs."""
        # Insert initial student
        self.add_test_student(101, 'Maheshwaran', 'AI&DS', 4, 8.1)
        
        # Attempt to insert another student with the duplicate ID 101
        data = {
            'id': '101',
            'name': 'Arun',
            'department': 'CSE',
            'year': '3',
            'cgpa': '7.9'
        }
        response = self.client.post('/add', data=data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Student ID already exists.', response.data)

    def test_add_student_validation_empty_name(self):
        """Test that a blank student name fails validation checks."""
        data = {
            'id': '102',
            'name': '',
            'department': 'CSE',
            'year': '3',
            'cgpa': '7.9'
        }
        response = self.client.post('/add', data=data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Name field is required.', response.data)

    def test_add_student_validation_year(self):
        """Test validation boundary constraints on year of study."""
        # Year too high
        data = {
            'id': '103',
            'name': 'Arun',
            'department': 'CSE',
            'year': '5',
            'cgpa': '7.9'
        }
        response = self.client.post('/add', data=data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Year must be between 1 and 4.', response.data)
        
        # Year too low
        data['year'] = '0'
        response = self.client.post('/add', data=data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Year must be between 1 and 4.', response.data)

    def test_add_student_validation_cgpa(self):
        """Test validation bounds for Cumulative GPA (CGPA)."""
        # CGPA too high
        data = {
            'id': '104',
            'name': 'Rohan',
            'department': 'ECE',
            'year': '2',
            'cgpa': '10.5'
        }
        response = self.client.post('/add', data=data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid CGPA.', response.data)
        
        # CGPA too low
        data['cgpa'] = '-0.1'
        response = self.client.post('/add', data=data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid CGPA.', response.data)

    def test_edit_student_success(self):
        """Test loading edit forms and successfully updating fields."""
        self.add_test_student(101, 'Maheshwaran', 'AI&DS', 4, 8.1)
        
        # Verify GET request fetches form prepopulated
        response = self.client.get('/edit/101')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Maheshwaran', response.data)
        self.assertIn(b'AI&amp;DS', response.data) # HTML-escaped check
        
        # Submit update payload
        edit_data = {
            'name': 'Maheshwaran Updated',
            'department': 'AI&DS Science',
            'year': '4',
            'cgpa': '9.2'
        }
        response = self.client.post('/edit/101', data=edit_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Student information updated successfully.', response.data)
        
        # Verify details directly in database
        with app.app.app_context():
            db = app.get_db()
            cursor = db.cursor()
            cursor.execute('SELECT * FROM students WHERE id = 101')
            row = cursor.fetchone()
            self.assertEqual(row['name'], 'Maheshwaran Updated')
            self.assertEqual(row['department'], 'AI&DS Science')
            self.assertEqual(row['cgpa'], 9.2)

    def test_delete_student(self):
        """Test permanent deletion of student record."""
        self.add_test_student(101, 'Maheshwaran', 'AI&DS', 4, 8.1)
        
        response = self.client.post('/delete/101', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Student deleted successfully.', response.data)
        
        # Verify deletion in database
        with app.app.app_context():
            db = app.get_db()
            cursor = db.cursor()
            cursor.execute('SELECT * FROM students WHERE id = 101')
            self.assertIsNone(cursor.fetchone())

    def test_search_student(self):
        """Test query routing search by ID or name details."""
        self.add_test_student(101, 'Maheshwaran', 'AI&DS', 4, 8.1)
        self.add_test_student(102, 'Arun', 'CSE', 3, 7.9)
        
        # Search by name substring
        response = self.client.get('/?search=Maheshwaran')
        self.assertIn(b'101', response.data)
        self.assertNotIn(b'Arun', response.data)
        
        # Search by exact numerical ID match
        response = self.client.get('/?search=102')
        self.assertIn(b'Arun', response.data)
        self.assertNotIn(b'Maheshwaran', response.data)

    def test_sorting_records(self):
        """Test sorting query parameter routing logic."""
        self.add_test_student(101, 'Maheshwaran', 'AI&DS', 4, 8.1)
        self.add_test_student(102, 'Arun', 'CSE', 3, 7.9)
        self.add_test_student(103, 'Zack', 'ECE', 1, 9.5)
        
        # Sort by cgpa ASC -> order should be Arun (7.9), Maheshwaran (8.1), Zack (9.5)
        response = self.client.get('/?sort=cgpa&direction=asc')
        data_str = response.data.decode('utf-8')
        idx_arun = data_str.find('Arun')
        idx_mahesh = data_str.find('Maheshwaran')
        idx_zack = data_str.find('Zack')
        
        self.assertTrue(idx_arun < idx_mahesh < idx_zack)
        
        # Sort by cgpa DESC -> order should be Zack (9.5), Maheshwaran (8.1), Arun (7.9)
        response = self.client.get('/?sort=cgpa&direction=desc')
        data_str = response.data.decode('utf-8')
        idx_arun = data_str.find('Arun')
        idx_mahesh = data_str.find('Maheshwaran')
        idx_zack = data_str.find('Zack')
        
        self.assertTrue(idx_zack < idx_mahesh < idx_arun)

if __name__ == '__main__':
    unittest.main()
