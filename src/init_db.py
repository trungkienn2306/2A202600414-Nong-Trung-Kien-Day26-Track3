from __future__ import annotations

import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "lab.sqlite3"

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS enrollments;
DROP TABLE IF EXISTS courses;
DROP TABLE IF EXISTS students;

CREATE TABLE students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    cohort TEXT NOT NULL,
    age INTEGER NOT NULL,
    email TEXT NOT NULL UNIQUE,
    score REAL NOT NULL
);

CREATE TABLE courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    credits INTEGER NOT NULL
);

CREATE TABLE enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    grade REAL NOT NULL,
    status TEXT NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students(id),
    FOREIGN KEY (course_id) REFERENCES courses(id)
);
"""

SEED_SQL = """
INSERT INTO students (name, cohort, age, email, score) VALUES
    ('An Nguyen', 'A1', 20, 'an@example.com', 88.5),
    ('Binh Tran', 'A1', 21, 'binh@example.com', 91.0),
    ('Chi Pham', 'B2', 20, 'chi@example.com', 77.0),
    ('Dung Le', 'B2', 22, 'dung@example.com', 84.25),
    ('Mai Vo', 'C3', 19, 'mai@example.com', 95.5);

INSERT INTO courses (code, title, credits) VALUES
    ('MCP101', 'Model Context Protocol', 3),
    ('DB201', 'Safe Database Access', 4),
    ('AI301', 'Applied AI Systems', 3);

INSERT INTO enrollments (student_id, course_id, grade, status) VALUES
    (1, 1, 89.0, 'active'),
    (1, 2, 86.5, 'active'),
    (2, 1, 92.0, 'active'),
    (3, 2, 78.0, 'completed'),
    (4, 3, 85.0, 'active'),
    (5, 1, 96.0, 'active');
"""


def create_database(db_path: str | Path = DEFAULT_DB_PATH) -> Path:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.executescript(SCHEMA_SQL)
        connection.executescript(SEED_SQL)
        connection.commit()
    return path


if __name__ == "__main__":
    database_path = create_database()
    print(f"Initialized SQLite database at {database_path}")
