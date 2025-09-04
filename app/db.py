import os
import psycopg2
from contextlib import contextmanager

DSN = os.getenv("AUDIT_DB_DSN")  # p.ej. postgresql://audit:audit@audit-db:5432/audit

@contextmanager
def get_conn():
    conn = psycopg2.connect(DSN)
    try:
        yield conn
    finally:
        conn.close()