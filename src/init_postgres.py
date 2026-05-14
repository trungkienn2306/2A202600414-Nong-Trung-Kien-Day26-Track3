from __future__ import annotations

import os

import psycopg
from psycopg.conninfo import conninfo_to_dict

from src.init_db import SEED_SQL

POSTGRES_SCHEMA_SQL = """
DROP TABLE IF EXISTS public.enrollments;
DROP TABLE IF EXISTS public.courses;
DROP TABLE IF EXISTS public.students;

CREATE TABLE public.students (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    cohort TEXT NOT NULL,
    age INTEGER NOT NULL,
    email TEXT NOT NULL UNIQUE,
    score REAL NOT NULL
);

CREATE TABLE public.courses (
    id SERIAL PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    credits INTEGER NOT NULL
);

CREATE TABLE public.enrollments (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES public.students(id),
    course_id INTEGER NOT NULL REFERENCES public.courses(id),
    grade REAL NOT NULL,
    status TEXT NOT NULL
);
"""


def create_postgres_database(dsn: str, *, allow_destructive_reset: bool = False) -> None:
    require_safe_reset_target(dsn, allow_destructive_reset=allow_destructive_reset)
    with psycopg.connect(dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute(POSTGRES_SCHEMA_SQL)
            cursor.execute(SEED_SQL)
        connection.commit()


def require_safe_reset_target(dsn: str, *, allow_destructive_reset: bool) -> None:
    if not allow_destructive_reset:
        raise RuntimeError("PostgreSQL reset requires allow_destructive_reset=True")
    dbname = str(conninfo_to_dict(dsn).get("dbname", ""))
    safe_tokens = ("lab", "test", "day26")
    if not dbname or not any(token in dbname.lower() for token in safe_tokens):
        raise RuntimeError("Refusing to reset PostgreSQL database without lab/test/day26 in dbname")


def main() -> None:
    dsn = os.environ["POSTGRES_DSN"]
    create_postgres_database(dsn, allow_destructive_reset=True)
    print("Initialized PostgreSQL database")


if __name__ == "__main__":
    main()
