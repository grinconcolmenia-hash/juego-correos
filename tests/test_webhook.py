from __future__ import annotations
import base64
import json
from unittest.mock import patch
import pytest
from app import create_app

@pytest.fixture
def client(tmp_path, monkeypatch):
    import database
    monkeypatch.setattr(database, "DATABASE_PATH", str(tmp_path / "test.db"))
    database.init_db()
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c

def _pubsub_payload(history_id: str) -> dict:
    inner = json.dumps({"historyId": history_id}).encode()
    encoded = base64.b64encode(inner).decode()
    return {"message": {"data": encoded}}

def test_webhook_missing_body_returns_200(client):
    res = client.post("/webhook", json={})
    assert res.status_code == 200
    assert res.get_json()["status"] == "ignored"

def test_webhook_processes_new_email(client):
    mock_email = {
        "id": "abc123",
        "remitente_nombre": "Ana García",
        "remitente_email": "ana@test.com",
        "asunto": "Colaboración",
        "cuerpo": "Hola equipo...",
        "fecha_recibido": "Thu, 23 Apr 2026 10:00:00 +0000",
    }
    mock_scores = {
        "puntaje_asunto": 8,
        "puntaje_persuasion": 7,
        "puntaje_contexto": 9,
        "puntaje_propuesta": 6,
        "puntaje_total": 7.5,
        "resumen": "Buen correo.",
    }
    with patch("webhook.get_new_message_ids", return_value=["abc123"]), \
         patch("webhook.get_email_data", return_value=mock_email), \
         patch("webhook.analyze_email", return_value=mock_scores):
        res = client.post("/webhook", json=_pubsub_payload("99999"))
    assert res.status_code == 200
    import database
    emails = database.get_all_emails_ranked()
    assert len(emails) == 1
    assert emails[0]["id"] == "abc123"

def test_webhook_skips_duplicate_email(client):
    mock_email = {
        "id": "dup1", "remitente_nombre": "X", "remitente_email": "x@x.com",
        "asunto": "Dup", "cuerpo": "...", "fecha_recibido": "2026-04-23",
    }
    mock_scores = {
        "puntaje_asunto": 5, "puntaje_persuasion": 5, "puntaje_contexto": 5,
        "puntaje_propuesta": 5, "puntaje_total": 5.0, "resumen": "ok",
    }
    with patch("webhook.get_new_message_ids", return_value=["dup1"]), \
         patch("webhook.get_email_data", return_value=mock_email), \
         patch("webhook.analyze_email", return_value=mock_scores):
        client.post("/webhook", json=_pubsub_payload("1000"))
        client.post("/webhook", json=_pubsub_payload("1001"))
    import database
    assert len(database.get_all_emails_ranked()) == 1
