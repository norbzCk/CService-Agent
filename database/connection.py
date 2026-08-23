import os
import logging
from contextlib import contextmanager
from typing import Any, Iterator

import psycopg2
import psycopg2.extras
from psycopg2 import pool as pg_pool
from psycopg2 import OperationalError, InterfaceError
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Local dev: postgresql://user:password@localhost:5432/dbname
# Supabase:  postgresql://postgres:[password]@[project-ref].supabase.co:5432/postgres
# (use the "Connection Pooling" URI from Supabase for production, port 6543)
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Add it to your .env file, e.g.\n"
        "DATABASE_URL=postgresql://user:password@localhost:5432/sokolink"
    )

MIN_CONN = int(os.environ.get("DB_POOL_MIN", 1))
MAX_CONN = int(os.environ.get("DB_POOL_MAX", 5))

_pool: pg_pool.SimpleConnectionPool | None = None


def get_pool() -> pg_pool.SimpleConnectionPool:
    """Create the connection pool once, lazily, and reuse it."""
    global _pool
    if _pool is None:
        try:
            _pool = pg_pool.SimpleConnectionPool(
                MIN_CONN,
                MAX_CONN,
                dsn=DATABASE_URL,
                sslmode=os.environ.get("DB_SSLMODE", "prefer"),
            )
            logger.info("Database connection pool created.")
        except OperationalError as error:
            logger.exception("Failed to create database connection pool.")
            raise
    return _pool


@contextmanager
def get_connection() -> Iterator[psycopg2.extensions.connection]:
    """
    Borrow a connection from the pool. Always returns it, even on error.

    Usage:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    """
    pool = get_pool()
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def run_query(query: str, params: tuple | dict | None = None) -> list[dict[str, Any]]:
    """
    Run a SELECT and return rows as a list of dicts.
    For INSERT/UPDATE/DELETE, use run_execute instead.
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]


def run_execute(query: str, params: tuple | dict | None = None) -> int:
    """Run an INSERT/UPDATE/DELETE. Returns affected row count."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.rowcount


def close_pool() -> None:
    """Call this on app shutdown."""
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None
        logger.info("Database connection pool closed.")