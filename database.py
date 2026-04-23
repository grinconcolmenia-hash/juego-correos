from __future__ import annotations

import sqlite3
import contextlib
from config import DATABASE_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS emails (
    id TEXT PRIMARY KEY,
    remitente_nombre TEXT,
    remitente_email TEXT,
    asunto TEXT,
    cuerpo TEXT,
    fecha_recibido TEXT,
    puntaje_asunto INTEGER,
    puntaje_persuasion INTEGER,
    puntaje_contexto INTEGER,
    puntaje_propuesta INTEGER,
    puntaje_gancho INTEGER,
    puntaje_personalizacion INTEGER,
    puntaje_unicidad INTEGER,
    puntaje_cta INTEGER,
    puntaje_total REAL,
    resumen_gemini TEXT,
    analizado_en TEXT
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""

@contextlib.contextmanager
def get_conn():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        # Migration: add new scoring columns if they don't exist
        existing = {row[1] for row in conn.execute("PRAGMA table_info(emails)").fetchall()}
        for col in ("puntaje_gancho", "puntaje_personalizacion", "puntaje_unicidad", "puntaje_cta"):
            if col not in existing:
                conn.execute(f"ALTER TABLE emails ADD COLUMN {col} INTEGER")

def save_email(record: dict):
    with get_conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO emails
               (id, remitente_nombre, remitente_email, asunto, cuerpo, fecha_recibido,
                puntaje_asunto, puntaje_persuasion, puntaje_contexto, puntaje_propuesta,
                puntaje_gancho, puntaje_personalizacion, puntaje_unicidad, puntaje_cta,
                puntaje_total, resumen_gemini, analizado_en)
               VALUES (:id, :remitente_nombre, :remitente_email, :asunto, :cuerpo,
                       :fecha_recibido, :puntaje_asunto, :puntaje_persuasion,
                       :puntaje_contexto, :puntaje_propuesta,
                       :puntaje_gancho, :puntaje_personalizacion, :puntaje_unicidad, :puntaje_cta,
                       :puntaje_total, :resumen_gemini, :analizado_en)""",
            record,
        )

def get_all_emails_ranked() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM emails ORDER BY puntaje_total DESC"
        ).fetchall()
        return [dict(row) for row in rows]

def get_setting(key: str) -> str | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else None

def set_setting(key: str, value: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )
