from __future__ import annotations

import base64
import json
from flask import Blueprint, request, jsonify
from gmail_service import get_new_message_ids, get_email_data
from gemini_service import analyze_email
import database

webhook_bp = Blueprint("webhook", __name__)


@webhook_bp.route("/webhook", methods=["POST"])
def handle_webhook():
    data = request.get_json() or {}

    # Check if message data exists
    if "message" not in data or "data" not in data.get("message", {}):
        return jsonify({"status": "ignored"}), 200

    # Decode the base64 message to get historyId
    try:
        encoded = data["message"]["data"]
        decoded = base64.b64decode(encoded).decode()
        payload = json.loads(decoded)
        history_id = payload.get("historyId")
    except (ValueError, KeyError, TypeError):
        return jsonify({"status": "ignored"}), 200

    if not history_id:
        return jsonify({"status": "ignored"}), 200

    # Get the last known history ID from settings
    last_history_id = database.get_setting("last_history_id") or "1"

    # Get new message IDs from Gmail
    message_ids = get_new_message_ids(history_id, last_history_id)

    # Process each new email
    for message_id in message_ids:
        _process_email(message_id)

    # Update the last known history ID
    database.set_setting("last_history_id", history_id)

    return jsonify({"status": "ok"}), 200


def _process_email(message_id: str):
    # Get email data from Gmail
    email_data = get_email_data(message_id)

    # Check if email already exists in database
    existing = database.get_all_emails_ranked()
    if any(e["id"] == message_id for e in existing):
        return

    # Analyze email with Gemini
    scores = analyze_email(email_data["asunto"], email_data["cuerpo"])

    # Prepare record for database
    record = {
        "id": email_data["id"],
        "remitente_nombre": email_data["remitente_nombre"],
        "remitente_email": email_data["remitente_email"],
        "asunto": email_data["asunto"],
        "cuerpo": email_data["cuerpo"],
        "fecha_recibido": email_data["fecha_recibido"],
        "puntaje_asunto": scores["puntaje_asunto"],
        "puntaje_persuasion": scores["puntaje_persuasion"],
        "puntaje_contexto": scores["puntaje_contexto"],
        "puntaje_propuesta": scores["puntaje_propuesta"],
        "puntaje_gancho": scores["puntaje_gancho"],
        "puntaje_personalizacion": scores["puntaje_personalizacion"],
        "puntaje_unicidad": scores["puntaje_unicidad"],
        "puntaje_cta": scores["puntaje_cta"],
        "puntaje_total": scores["puntaje_total"],
        "resumen_gemini": scores["resumen"],
        "analizado_en": None,
    }

    # Save to database
    database.save_email(record)
