from __future__ import annotations
import threading
import time
from datetime import datetime, timezone
from flask import Flask, jsonify, render_template
from database import init_db, get_all_emails_ranked, get_setting, set_setting, save_email, get_conn
from webhook import webhook_bp

def _poll_gmail():
    from gmail_service import get_inbox_message_ids, get_email_data
    from gemini_service import analyze_email
    time.sleep(3)  # wait for Flask to start
    print("[poller] Gmail polling started")
    while True:
        try:
            ids = get_inbox_message_ids()
            processed_raw = get_setting("processed_ids") or ""
            processed = set(processed_raw.split(",")) if processed_raw else set()
            new_ids = [i for i in ids if i not in processed]
            for msg_id in new_ids:
                try:
                    email_data = get_email_data(msg_id)
                    scores = analyze_email(email_data["asunto"], email_data["cuerpo"])
                    record = {**email_data, "puntaje_asunto": scores["puntaje_asunto"], "puntaje_persuasion": scores["puntaje_persuasion"], "puntaje_contexto": scores["puntaje_contexto"], "puntaje_propuesta": scores["puntaje_propuesta"], "puntaje_gancho": scores["puntaje_gancho"], "puntaje_personalizacion": scores["puntaje_personalizacion"], "puntaje_unicidad": scores["puntaje_unicidad"], "puntaje_cta": scores["puntaje_cta"], "puntaje_total": scores["puntaje_total"], "resumen_gemini": scores["resumen"], "analizado_en": datetime.now(timezone.utc).isoformat()}
                    save_email(record)
                    processed.add(msg_id)
                    set_setting("processed_ids", ",".join(processed))
                    print(f"[poller] procesado: {email_data['asunto']} — {scores['puntaje_total']}/10")
                except Exception as e:
                    print(f"[poller] error en {msg_id}: {e}")
        except Exception as e:
            print(f"[poller] error general: {e}")
        time.sleep(10)

def create_app():
    app = Flask(__name__)
    app.register_blueprint(webhook_bp)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/emails")
    def api_emails():
        return jsonify(get_all_emails_ranked())

    @app.route("/api/clear", methods=["POST"])
    def api_clear():
        with get_conn() as conn:
            conn.execute("DELETE FROM emails")
        set_setting("processed_ids", "")
        return jsonify({"status": "ok"})

    return app

init_db()
app = create_app()

if __name__ == "__main__":
    t = threading.Thread(target=_poll_gmail, daemon=True)
    t.start()
    app.run(debug=False, port=5000)
