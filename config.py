import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GMAIL_CREDENTIALS_FILE = os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
GMAIL_TOKEN_FILE = os.getenv("GMAIL_TOKEN_FILE", "token.json")
PUBSUB_TOPIC = os.getenv("PUBSUB_TOPIC")
DATABASE_PATH = os.getenv("DATABASE_PATH", "emails.db")
