"""Shared SQLAlchemy engine and database-initialisation helpers."""
import os
from pathlib import Path

from sqlalchemy import create_engine, text

BASE_DIR = Path(__file__).resolve().parent
SQL_DIR = BASE_DIR / "sql"

DEFAULT_URL = "postgresql+psycopg2://postgres:postgres@localhost:5433/conference"


def database_url() -> str:
    url = os.environ.get("DATABASE_URL", DEFAULT_URL)
    # Hosting providers often hand out postgres:// URLs; SQLAlchemy needs postgresql://
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


engine = create_engine(database_url(), pool_pre_ping=True)


def read_sql(name: str) -> str:
    return (SQL_DIR / name).read_text(encoding="utf-8")


def run_script(conn, name: str) -> None:
    """Execute a multi-statement .sql file on an open SQLAlchemy connection."""
    conn.exec_driver_sql(read_sql(name))


def reset_database() -> None:
    """Drop and recreate all tables, load the seed data and create the view."""
    with engine.begin() as conn:
        run_script(conn, "schema.sql")
        run_script(conn, "seed.sql")
        run_script(conn, "view.sql")


def is_initialised() -> bool:
    with engine.connect() as conn:
        return conn.execute(text("SELECT to_regclass('public.app_user') IS NOT NULL")).scalar()
