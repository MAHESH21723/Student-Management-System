# StudentSpace | Student Management System

StudentSpace is a modern, responsive full-stack web application designed to manage student records efficiently. Built using Python Flask, SQLite, Bootstrap 5, and custom glassmorphism styles, it features database persistence, secure SQL parameterization, client & server-side validation, and sorting capabilities.

This project was built as a premium portfolio showcase demonstrating clean architecture, defensive coding practices, and visually stunning web interfaces.

---

## 🚀 Key Features

* **Complete CRUD Operations**: Create, read, update, and delete student data dynamically.
* **Premium Glassmorphic UI**: High-fidelity dark mode with gradients, dynamic buttons, hover animations, and customized typography using Google Fonts (Outfit & Plus Jakarta Sans).
* **Live Stats Counters**: Dynamic cards displaying Total Students, Average CGPA, Unique Departments, and Top Class CGPA.
* **Advanced Query Controls**: Search instantly by name or student ID, and sort dynamically across all columns in ascending/descending order.
* **Data Security & SQL Injection Protection**: Fully parameterized queries to prevent SQL injections.
* **Double-Layer Validation**: Matches input rules on both the frontend (HTML5 types and selects) and backend (checking bounds, empty fields, and ID duplication) with clean alert banners.
* **Safe Deletions**: Deletes records safely through a custom confirmation modal that displays student context before execution.

---

## 🛠️ Tech Stack

* **Backend**: Python 3.x, Flask (Web Server & Route Handler).
* **Database**: SQLite (Local embedded database stored in `students.db`).
* **Frontend**: HTML5, CSS3 (Custom Styles), Bootstrap 5, and Bootstrap Icons.

---

## 📂 Project Directory Structure

```text
StudentManagementSystem/
│
├── app.py                # Flask main application script
├── students.db           # SQLite database file (generated automatically)
├── requirements.txt      # Python package dependencies
│
├── templates/            # Jinja2 template directories
│   ├── index.html        # Main dashboard list and search panel
│   ├── add_student.html  # Student registration form
│   └── edit_student.html # Student modification form
│
├── static/               # Static assets
│   └── css/
│       └── style.css     # Custom theme CSS and animations
│
└── README.md             # Project documentation
```

---

## 📊 Database Design

The application uses an SQLite database (`students.db`) with a single table named `students`.

### `students` Table Schema

| Column | Data Type | Key Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | Primary Key, Not Null | Unique Student ID |
| `name` | `TEXT` | Not Null | Full student name |
| `department` | `TEXT` | Not Null | Department name / code |
| `year` | `INTEGER` | Not Null | Academic Year (1 to 4) |
| `cgpa` | `REAL` | Not Null | Cumulative GPA (0.0 to 10.0) |

---

## 💻 Validation Rules & Error Flashing

The system enforces the following business logic rules:

1. **Student ID**: Must be a positive integer and **cannot be duplicated** in the database.
   * *Error*: `"Student ID already exists."`
2. **Student Name**: Cannot be blank or empty.
   * *Error*: `"Name field is required."`
3. **Academic Year**: Must be an integer between 1 and 4.
   * *Error*: `"Year must be between 1 and 4."`
4. **CGPA**: Must be a decimal value between 0.00 and 10.00.
   * *Error*: `"Invalid CGPA."`

---

## ⚙️ Installation & Run Instructions

### Prerequisites

Ensure you have Python 3.x installed on your computer.

### Step 1: Clone or Navigate to the Directory
Open your terminal inside the project folder:
```bash
cd "d:/python project"
```

### Step 2: Install Dependencies
Install the required packages using `pip`:
```bash
pip install -r requirements.txt
```

### Step 3: Run the Flask Application
Start the development server:
```bash
python app.py
```

### Step 4: Access in Browser
Once running, open your web browser and navigate to:
```text
http://localhost:5000
```
