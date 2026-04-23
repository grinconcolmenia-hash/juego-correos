from __future__ import annotations
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

def get_inbox_message_ids() -> list[str]:
    service = get_gmail_service()
    try:
        results = service.users().messages().list(
            userId="me", labelIds=["INBOX"], maxResults=50
        ).execute()
        return [m["id"] for m in results.get("messages", [])]
    except Exception as e:
        print(f"[gmail] inbox list error: {e}")
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
