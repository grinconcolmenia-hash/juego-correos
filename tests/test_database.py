import os
import pytest
import database

TEST_DB = "test_emails.db"

@pytest.fixture(autouse=True)
def use_test_db(monkeypatch, tmp_path):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(database, "DATABASE_PATH", db_path)
    database.init_db()
    yield

def test_init_db_creates_tables():
    import sqlite3
    conn = sqlite3.connect(database.DATABASE_PATH)
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    conn.close()
    assert "emails" in tables
    assert "settings" in tables

def test_save_and_retrieve_email():
    record = {
        "id": "msg1",
        "remitente_nombre": "Juan Pérez",
        "remitente_email": "juan@test.com",
        "asunto": "Oferta especial",
        "cuerpo": "Hola, tengo una propuesta...",
        "fecha_recibido": "2026-04-23T10:00:00",
        "puntaje_asunto": 8,
        "puntaje_persuasion": 7,
        "puntaje_contexto": 9,
        "puntaje_propuesta": 6,
        "puntaje_total": 7.5,
        "resumen_gemini": "Buen asunto, propuesta mejorable.",
        "analizado_en": "2026-04-23T10:00:05",
    }
    database.save_email(record)
    emails = database.get_all_emails_ranked()
    assert len(emails) == 1
    assert emails[0]["id"] == "msg1"
    assert emails[0]["puntaje_total"] == 7.5

def test_get_all_emails_ranked_orders_by_score():
    for i, score in enumerate([5.0, 9.0, 7.0]):
        database.save_email({
            "id": f"msg{i}", "remitente_nombre": "A", "remitente_email": "a@b.com",
            "asunto": "X", "cuerpo": "Y", "fecha_recibido": "2026-04-23",
            "puntaje_asunto": 5, "puntaje_persuasion": 5, "puntaje_contexto": 5,
            "puntaje_propuesta": 5, "puntaje_total": score,
            "resumen_gemini": "ok", "analizado_en": "2026-04-23",
        })
    emails = database.get_all_emails_ranked()
    scores = [e["puntaje_total"] for e in emails]
    assert scores == sorted(scores, reverse=True)

def test_settings_get_and_set():
    assert database.get_setting("history_id") is None
    database.set_setting("history_id", "12345")
    assert database.get_setting("history_id") == "12345"
    database.set_setting("history_id", "99999")
    assert database.get_setting("history_id") == "99999"
