# Email Ranking Board — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Flask web app that reads incoming emails from claude.comercial@gmail.com in real time, scores them with Gemini API across 4 dimensions (1-10 each), and displays a live public ranking board.

**Architecture:** Gmail Push Notifications (via Google Cloud Pub/Sub) POST to a Flask /webhook endpoint. Flask reads the full email via Gmail API, sends it to Gemini API for scoring, persists results in SQLite, and serves a board HTML page that polls /api/emails every 3 seconds.

**Tech Stack:** Python 3.11+, Flask, google-generativeai, google-api-python-client, SQLite, Vanilla JS, ngrok (for local webhook during demo)

---

## File Map

| File | Responsibility |
|------|---------------|
| `app.py` | Flask entry point, registers blueprint, serves `/` and `/api/emails` |
| `config.py` | Reads env vars via dotenv |
| `database.py` | SQLite schema, `save_email`, `get_all_emails_ranked`, `get_setting`, `set_setting` |
| `gemini_service.py` | Calls Gemini API, returns 4 scores + resumen + puntaje_total |
| `gmail_service.py` | OAuth2 auth, `get_email_data`, `get_new_message_ids`, `setup_gmail_watch` |
| `webhook.py` | Flask Blueprint, POST `/webhook`, orchestrates Gmail→Gemini→DB |
| `templates/index.html` | Board HTML shell |
| `static/styles.css` | Dark theme, card layout, animations |
| `static/app.js` | Polling loop, render ranking, toggle card expand |
| `requirements.txt` | Python dependencies |
| `.env.example` | Env var template |
| `tests/test_database.py` | Unit tests for DB functions |
| `tests/test_gemini_service.py` | Unit tests for scoring logic (mocked API) |
| `tests/test_webhook.py` | Unit tests for webhook handler (mocked services) |

---

## Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `config.py`

- [ ] **Step 1: Create requirements.txt**

```
flask>=3.0.0
google-generativeai>=0.8.0
google-api-python-client>=2.150.0
google-auth-httplib2>=0.2.0
google-auth-oauthlib>=1.2.0
python-dotenv>=1.0.0
pytest>=8.0.0
```

- [ ] **Step 2: Create .env.example**

```
GEMINI_API_KEY=your_gemini_api_key_here
GMAIL_CREDENTIALS_FILE=credentials.json
GMAIL_TOKEN_FILE=token.json
PUBSUB_TOPIC=projects/YOUR_PROJECT_ID/topics/YOUR_TOPIC_NAME
DATABASE_PATH=emails.db
```

- [ ] **Step 3: Create config.py**

```python
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GMAIL_CREDENTIALS_FILE = os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
GMAIL_TOKEN_FILE = os.getenv("GMAIL_TOKEN_FILE", "token.json")
PUBSUB_TOPIC = os.getenv("PUBSUB_TOPIC")
DATABASE_PATH = os.getenv("DATABASE_PATH", "emails.db")
```

- [ ] **Step 4: Install dependencies**

```bash
python -m venv venv
venv/Scripts/activate   # Windows
pip install -r requirements.txt
```

Expected: all packages install without errors.

- [ ] **Step 5: Copy .env and fill in values**

```bash
cp .env.example .env
```

Fill in `GEMINI_API_KEY` from https://aistudio.google.com/app/apikey

- [ ] **Step 6: Commit**

```bash
git init
git add requirements.txt .env.example config.py
git commit -m "feat: project setup and config"
```

---

## Task 2: Database

**Files:**
- Create: `database.py`
- Create: `tests/test_database.py`

- [ ] **Step 1: Write failing tests**

Create `tests/__init__.py` (empty), then `tests/test_database.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_database.py -v
```

Expected: `ModuleNotFoundError: No module named 'database'`

- [ ] **Step 3: Create database.py**

```python
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

def save_email(record: dict):
    with get_conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO emails
               (id, remitente_nombre, remitente_email, asunto, cuerpo, fecha_recibido,
                puntaje_asunto, puntaje_persuasion, puntaje_contexto, puntaje_propuesta,
                puntaje_total, resumen_gemini, analizado_en)
               VALUES (:id, :remitente_nombre, :remitente_email, :asunto, :cuerpo,
                       :fecha_recibido, :puntaje_asunto, :puntaje_persuasion,
                       :puntaje_contexto, :puntaje_propuesta, :puntaje_total,
                       :resumen_gemini, :analizado_en)""",
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_database.py -v
```

Expected: 4 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add database.py tests/
git commit -m "feat: sqlite database with email schema and settings"
```

---

## Task 3: Gemini Service

**Files:**
- Create: `gemini_service.py`
- Create: `tests/test_gemini_service.py`

- [ ] **Step 1: Write failing tests**

`tests/test_gemini_service.py`:

```python
import json
from unittest.mock import MagicMock, patch
import gemini_service

MOCK_RESPONSE_JSON = json.dumps({
    "puntaje_asunto": 8,
    "puntaje_persuasion": 7,
    "puntaje_contexto": 9,
    "puntaje_propuesta": 6,
    "resumen": "Buen asunto pero propuesta débil.",
})

def _mock_model(response_text):
    mock_response = MagicMock()
    mock_response.text = response_text
    mock_model = MagicMock()
    mock_model.generate_content.return_value = mock_response
    return mock_model

def test_analyze_email_returns_scores():
    with patch.object(gemini_service, "model", _mock_model(MOCK_RESPONSE_JSON)):
        result = gemini_service.analyze_email("Oferta única", "Hola, te escribo porque...")
    assert result["puntaje_asunto"] == 8
    assert result["puntaje_persuasion"] == 7
    assert result["puntaje_contexto"] == 9
    assert result["puntaje_propuesta"] == 6
    assert result["puntaje_total"] == 7.5
    assert "resumen" in result

def test_analyze_email_strips_markdown_code_block():
    wrapped = "```json\n" + MOCK_RESPONSE_JSON + "\n```"
    with patch.object(gemini_service, "model", _mock_model(wrapped)):
        result = gemini_service.analyze_email("Asunto", "Cuerpo")
    assert result["puntaje_total"] == 7.5

def test_puntaje_total_is_average():
    data = {
        "puntaje_asunto": 10,
        "puntaje_persuasion": 10,
        "puntaje_contexto": 10,
        "puntaje_propuesta": 10,
        "resumen": "Perfecto.",
    }
    with patch.object(gemini_service, "model", _mock_model(json.dumps(data))):
        result = gemini_service.analyze_email("X", "Y")
    assert result["puntaje_total"] == 10.0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_gemini_service.py -v
```

Expected: `ModuleNotFoundError: No module named 'gemini_service'`

- [ ] **Step 3: Create gemini_service.py**

```python
import json
import google.generativeai as genai
from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

_PROMPT = """Eres un experto evaluador de correos electrónicos comerciales.
Analiza el siguiente correo y devuelve ÚNICAMENTE un JSON válido, sin texto adicional:

{{
  "puntaje_asunto": <entero 1-10>,
  "puntaje_persuasion": <entero 1-10>,
  "puntaje_contexto": <entero 1-10>,
  "puntaje_propuesta": <entero 1-10>,
  "resumen": "<2-3 líneas sobre fortalezas y debilidades>"
}}

Criterios:
- puntaje_asunto: ¿Qué tan atractivo, intrigante y no-spam es el subject?
- puntaje_persuasion: ¿Qué tan convincente, amable y bien redactado está el cuerpo?
- puntaje_contexto: ¿Aporta contexto? ¿Se entiende quién escribe y por qué?
- puntaje_propuesta: ¿La propuesta de valor es clara, relevante e interesante?

Asunto: {asunto}

Cuerpo:
{cuerpo}
"""

def analyze_email(asunto: str, cuerpo: str) -> dict:
    prompt = _PROMPT.format(asunto=asunto, cuerpo=cuerpo)
    response = model.generate_content(prompt)
    text = response.text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    data = json.loads(text)
    data["puntaje_total"] = round(
        (data["puntaje_asunto"] + data["puntaje_persuasion"] +
         data["puntaje_contexto"] + data["puntaje_propuesta"]) / 4,
        2,
    )
    return data
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_gemini_service.py -v
```

Expected: 3 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add gemini_service.py tests/test_gemini_service.py
git commit -m "feat: gemini service for email scoring"
```

---

## Task 4: Gmail Service

**Files:**
- Create: `gmail_service.py`

> Note: Gmail API requires real OAuth2 credentials — unit tests mock the service client entirely.

- [ ] **Step 1: Create gmail_service.py**

```python
import base64
import re
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from config import GMAIL_CREDENTIALS_FILE, GMAIL_TOKEN_FILE, PUBSUB_TOPIC

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

def get_gmail_service():
    creds = None
    if os.path.exists(GMAIL_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(GMAIL_TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                GMAIL_CREDENTIALS_FILE, SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open(GMAIL_TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)

def get_email_data(message_id: str) -> dict:
    service = get_gmail_service()
    msg = service.users().messages().get(
        userId="me", id=message_id, format="full"
    ).execute()
    headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
    asunto = headers.get("Subject", "(Sin asunto)")
    from_header = headers.get("From", "")
    fecha = headers.get("Date", "")
    remitente_nombre, remitente_email = _parse_from(from_header)
    cuerpo = _extract_body(msg["payload"])
    return {
        "id": message_id,
        "remitente_nombre": remitente_nombre,
        "remitente_email": remitente_email,
        "asunto": asunto,
        "cuerpo": cuerpo,
        "fecha_recibido": fecha,
    }

def get_new_message_ids(history_id: str, last_history_id: str) -> list[str]:
    service = get_gmail_service()
    try:
        history = service.users().history().list(
            userId="me",
            startHistoryId=last_history_id,
            historyTypes=["messageAdded"],
        ).execute()
        ids = []
        for record in history.get("history", []):
            for msg in record.get("messagesAdded", []):
                ids.append(msg["message"]["id"])
        return ids
    except Exception as e:
        print(f"[gmail] history list error: {e}")
        return []

def setup_gmail_watch() -> str:
    service = get_gmail_service()
    result = service.users().watch(
        userId="me",
        body={"topicName": PUBSUB_TOPIC, "labelIds": ["INBOX"]},
    ).execute()
    return str(result["historyId"])

def _parse_from(from_header: str) -> tuple[str, str]:
    match = re.match(r'"?([^"<]+)"?\s*<?([^>]*)>?', from_header)
    if match:
        name = match.group(1).strip()
        addr = match.group(2).strip() or name
        return name, addr
    return from_header, from_header

def _extract_body(payload: dict) -> str:
    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain":
                data = part["body"].get("data", "")
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
        return _extract_body(payload["parts"][0])
    data = payload.get("body", {}).get("data", "")
    if data:
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    return ""
```

- [ ] **Step 2: Commit**

```bash
git add gmail_service.py
git commit -m "feat: gmail service with oauth2 and email reader"
```

---

## Task 5: Webhook Handler

**Files:**
- Create: `webhook.py`
- Create: `tests/test_webhook.py`

- [ ] **Step 1: Write failing tests**

`tests/test_webhook.py`:

```python
import base64
import json
from unittest.mock import patch, MagicMock
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_webhook.py -v
```

Expected: `ModuleNotFoundError` or `ImportError`

- [ ] **Step 3: Create webhook.py**

```python
import base64
import json
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from database import save_email, get_setting, set_setting
from gmail_service import get_email_data, get_new_message_ids
from gemini_service import analyze_email

webhook_bp = Blueprint("webhook", __name__)

@webhook_bp.route("/webhook", methods=["POST"])
def handle_webhook():
    data = request.get_json(silent=True)
    if not data or "message" not in data:
        return jsonify({"status": "ignored"}), 200

    payload = json.loads(
        base64.b64decode(data["message"]["data"]).decode("utf-8")
    )
    history_id = str(payload.get("historyId", ""))
    last_history_id = get_setting("last_history_id")

    if last_history_id is None:
        last_history_id = str(int(history_id) - 1)

    message_ids = get_new_message_ids(history_id, last_history_id)
    set_setting("last_history_id", history_id)

    for msg_id in message_ids:
        _process_email(msg_id)

    return jsonify({"status": "ok"}), 200

def _process_email(message_id: str):
    try:
        email_data = get_email_data(message_id)
        scores = analyze_email(email_data["asunto"], email_data["cuerpo"])
        record = {
            **email_data,
            **scores,
            "analizado_en": datetime.now(timezone.utc).isoformat(),
        }
        save_email(record)
    except Exception as e:
        print(f"[webhook] error processing {message_id}: {e}")
```

- [ ] **Step 4: Create app.py (needed for tests)**

```python
from flask import Flask, jsonify, render_template
from database import init_db, get_all_emails_ranked
from webhook import webhook_bp

def create_app():
    app = Flask(__name__)
    app.register_blueprint(webhook_bp)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/emails")
    def api_emails():
        return jsonify(get_all_emails_ranked())

    return app

if __name__ == "__main__":
    init_db()
    app = create_app()
    app.run(debug=True, port=5000)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_webhook.py -v
```

Expected: 3 tests PASSED.

- [ ] **Step 6: Commit**

```bash
git add webhook.py app.py tests/test_webhook.py
git commit -m "feat: webhook handler and flask app"
```

---

## Task 6: Board Frontend

**Files:**
- Create: `templates/index.html`
- Create: `static/styles.css`
- Create: `static/app.js`

- [ ] **Step 1: Create templates/index.html**

```html
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Ranking — Correos Comerciales</title>
  <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
  <header>
    <h1>RANKING DE CORREOS COMERCIALES</h1>
    <div class="live-badge">
      <span class="pulse"></span>
      EN VIVO
    </div>
  </header>
  <main id="board">
    <div class="empty-state">Esperando correos...</div>
  </main>
  <script src="/static/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create static/styles.css**

```css
:root {
  --bg: #0f172a;
  --card: #1e293b;
  --card-hover: #263548;
  --text: #f1f5f9;
  --muted: #94a3b8;
  --green: #22c55e;
  --yellow: #eab308;
  --red: #ef4444;
  --accent: #6366f1;
  --border: #334155;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  background: var(--bg);
  color: var(--text);
  font-family: 'Segoe UI', system-ui, sans-serif;
  min-height: 100vh;
}

header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.25rem 2rem;
  background: var(--card);
  border-bottom: 3px solid var(--accent);
  position: sticky;
  top: 0;
  z-index: 10;
}

h1 {
  font-size: 1.5rem;
  font-weight: 800;
  letter-spacing: 0.05em;
}

.live-badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--green);
  letter-spacing: 0.12em;
}

.pulse {
  width: 10px;
  height: 10px;
  background: var(--green);
  border-radius: 50%;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.3; transform: scale(1.4); }
}

main {
  padding: 1.5rem 2rem;
  max-width: 860px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.empty-state {
  text-align: center;
  color: var(--muted);
  padding: 4rem;
  font-size: 1.1rem;
}

.card {
  background: var(--card);
  border-radius: 10px;
  padding: 0.9rem 1.1rem;
  cursor: pointer;
  border-left: 5px solid transparent;
  animation: slideIn 0.35s ease;
  transition: background 0.15s;
}

.card:hover { background: var(--card-hover); }

.card.green  { border-left-color: var(--green); }
.card.yellow { border-left-color: var(--yellow); }
.card.red    { border-left-color: var(--red); }

@keyframes slideIn {
  from { opacity: 0; transform: translateY(-10px); }
  to   { opacity: 1; transform: translateY(0); }
}

.card-header {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.rank {
  font-size: 1.4rem;
  font-weight: 800;
  color: var(--accent);
  min-width: 2.2rem;
}

.sender { flex: 1; }

.sender-name  { font-size: 1rem; font-weight: 600; }
.sender-email { font-size: 0.78rem; color: var(--muted); margin-top: 1px; }

.score-area {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  min-width: 110px;
}

.score-number {
  font-size: 1.5rem;
  font-weight: 800;
  line-height: 1;
}

.card.green  .score-number { color: var(--green); }
.card.yellow .score-number { color: var(--yellow); }
.card.red    .score-number { color: var(--red); }

.score-bar {
  width: 90px;
  height: 5px;
  background: var(--border);
  border-radius: 3px;
  overflow: hidden;
}

.score-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease;
}

.card.green  .score-fill { background: var(--green); }
.card.yellow .score-fill { background: var(--yellow); }
.card.red    .score-fill { background: var(--red); }

.card-body {
  display: none;
  margin-top: 0.85rem;
  padding-top: 0.85rem;
  border-top: 1px solid var(--border);
}

.card.expanded .card-body { display: block; }

.subject {
  font-size: 0.88rem;
  margin-bottom: 0.7rem;
  color: var(--muted);
}

.subject span { color: var(--text); font-weight: 600; }

.dimensions {
  display: flex;
  gap: 0.6rem;
  flex-wrap: wrap;
  margin-bottom: 0.7rem;
}

.dim {
  background: var(--bg);
  border-radius: 6px;
  padding: 0.3rem 0.6rem;
  font-size: 0.78rem;
}

.dim-label { color: var(--muted); }
.dim-score { font-weight: 700; margin-left: 0.25rem; color: var(--text); }

.resumen {
  font-size: 0.83rem;
  color: var(--muted);
  line-height: 1.55;
  font-style: italic;
  margin-bottom: 0.7rem;
}

.cuerpo {
  font-size: 0.82rem;
  color: #cbd5e1;
  line-height: 1.65;
  white-space: pre-wrap;
  background: var(--bg);
  padding: 0.75rem;
  border-radius: 8px;
  max-height: 280px;
  overflow-y: auto;
}
```

- [ ] **Step 3: Create static/app.js**

```javascript
let knownIds = new Set();
let lastData = "";

function colorClass(score) {
  if (score >= 8) return "green";
  if (score >= 5) return "yellow";
  return "red";
}

function esc(str) {
  return String(str || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderCard(email, rank) {
  const cls = colorClass(email.puntaje_total);
  const fillPct = ((email.puntaje_total / 10) * 100).toFixed(1);
  const isNew = !knownIds.has(email.id);
  return `
    <div class="card ${cls}${isNew ? " new" : ""}" id="card-${esc(email.id)}"
         onclick="toggleCard('${esc(email.id)}')">
      <div class="card-header">
        <div class="rank">#${rank}</div>
        <div class="sender">
          <div class="sender-name">${esc(email.remitente_nombre || email.remitente_email)}</div>
          <div class="sender-email">${esc(email.remitente_email)}</div>
        </div>
        <div class="score-area">
          <div class="score-number">${Number(email.puntaje_total).toFixed(1)}</div>
          <div class="score-bar">
            <div class="score-fill" style="width:${fillPct}%"></div>
          </div>
        </div>
      </div>
      <div class="card-body">
        <div class="subject">Asunto: <span>${esc(email.asunto)}</span></div>
        <div class="dimensions">
          <div class="dim"><span class="dim-label">Asunto</span>
            <span class="dim-score">${email.puntaje_asunto}/10</span></div>
          <div class="dim"><span class="dim-label">Persuasión</span>
            <span class="dim-score">${email.puntaje_persuasion}/10</span></div>
          <div class="dim"><span class="dim-label">Contexto</span>
            <span class="dim-score">${email.puntaje_contexto}/10</span></div>
          <div class="dim"><span class="dim-label">Propuesta</span>
            <span class="dim-score">${email.puntaje_propuesta}/10</span></div>
        </div>
        <div class="resumen">"${esc(email.resumen_gemini)}"</div>
        <div class="cuerpo">${esc(email.cuerpo)}</div>
      </div>
    </div>`;
}

function toggleCard(id) {
  const card = document.getElementById("card-" + id);
  if (card) card.classList.toggle("expanded");
}

async function fetchAndRender() {
  try {
    const res = await fetch("/api/emails");
    const emails = await res.json();
    const serialized = JSON.stringify(emails);
    if (serialized === lastData) return;
    lastData = serialized;

    const board = document.getElementById("board");
    if (emails.length === 0) {
      board.innerHTML = '<div class="empty-state">Esperando correos...</div>';
      return;
    }
    board.innerHTML = emails.map((e, i) => renderCard(e, i + 1)).join("");
    emails.forEach(e => knownIds.add(e.id));
  } catch (err) {
    console.error("fetch error:", err);
  }
}

fetchAndRender();
setInterval(fetchAndRender, 3000);
```

- [ ] **Step 4: Run the app and verify the board loads**

```bash
python app.py
```

Open http://localhost:5000 — should show the board with "Esperando correos..." message and the pulsing EN VIVO badge.

- [ ] **Step 5: Commit**

```bash
git add templates/ static/
git commit -m "feat: board frontend with live polling and card expand"
```

---

## Task 7: Gmail Pub/Sub Setup

> This task is a manual setup task — no code to write, no tests. Execute these steps once before the demo.

- [ ] **Step 1: Create a Google Cloud project**

Go to https://console.cloud.google.com → New Project → name it `colmen-email-board`

- [ ] **Step 2: Enable Gmail API**

In the project: APIs & Services → Enable APIs → search "Gmail API" → Enable

- [ ] **Step 3: Enable Pub/Sub API**

APIs & Services → Enable APIs → search "Cloud Pub/Sub" → Enable

- [ ] **Step 4: Create OAuth2 credentials**

APIs & Services → Credentials → Create Credentials → OAuth Client ID → Desktop App → Download JSON → save as `credentials.json` in project root

- [ ] **Step 5: Create Pub/Sub topic**

```bash
gcloud pubsub topics create gmail-push --project=colmen-email-board
```

- [ ] **Step 6: Grant Gmail permission to publish to the topic**

```bash
gcloud pubsub topics add-iam-policy-binding gmail-push \
  --member="serviceAccount:gmail-api-push@system.gserviceaccount.com" \
  --role="roles/pubsub.publisher" \
  --project=colmen-email-board
```

- [ ] **Step 7: Create Pub/Sub push subscription pointing to ngrok**

First install ngrok: https://ngrok.com/download  
Start ngrok (in a separate terminal):

```bash
ngrok http 5000
```

Copy the HTTPS URL (e.g. `https://abc123.ngrok-free.app`), then:

```bash
gcloud pubsub subscriptions create gmail-push-sub \
  --topic=gmail-push \
  --push-endpoint=https://abc123.ngrok-free.app/webhook \
  --project=colmen-email-board
```

- [ ] **Step 8: Update .env with Pub/Sub topic**

```
PUBSUB_TOPIC=projects/colmen-email-board/topics/gmail-push
```

- [ ] **Step 9: Authenticate Gmail and set up watch**

```bash
python -c "from gmail_service import setup_gmail_watch; hid = setup_gmail_watch(); print('Watch started, historyId:', hid)"
```

A browser window will open for OAuth2 — log in with claude.comercial@gmail.com. After auth, `token.json` is saved. The watch is now active.

- [ ] **Step 10: Run the app and send a test email**

```bash
python app.py
```

Send an email to claude.comercial@gmail.com. Within seconds it should appear on the board at http://localhost:5000.

- [ ] **Step 11: Commit**

```bash
git add .env.example
git commit -m "docs: gmail pubsub setup complete"
```

---

## Self-Review

**Spec coverage:**
- [x] Gmail Push Notifications → Task 7
- [x] Gemini API scoring → Task 3
- [x] 4 dimensions 1-10, promedio = puntaje_total → Task 3
- [x] SQLite persistence → Task 2
- [x] `/api/emails` ranked endpoint → Task 5 (app.py)
- [x] Board with polling every 3s → Task 6 (app.js)
- [x] Card expand on click → Task 6
- [x] Color badges green/yellow/red → Task 6
- [x] EN VIVO badge → Task 6
- [x] ngrok for local webhook → Task 7

**Placeholder scan:** No TBDs, no "implement later", all code blocks present.

**Type consistency:** `save_email` takes `dict`, `get_all_emails_ranked` returns `list[dict]`, both consistent across Tasks 2, 5. `analyze_email` returns `dict` with keys `puntaje_*` and `resumen` — matches `webhook.py` spread operator usage.
