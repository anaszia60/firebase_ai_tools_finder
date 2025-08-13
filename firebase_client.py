# firebase_client.py
import os
from pathlib import Path
from dotenv import load_dotenv
import pyrebase  # pip install pyrebase4

# Load .env from this folder
ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)

_config = {
    "apiKey": os.getenv("FIREBASE_API_KEY"),
    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
    "projectId": os.getenv("FIREBASE_PROJECT_ID"),
    "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
    "appId": os.getenv("FIREBASE_APP_ID"),
    "measurementId": os.getenv("FIREBASE_MEASUREMENT_ID"),
    "databaseURL": os.getenv("FIREBASE_DATABASE_URL"),
}

_firebase = _auth = _db = _storage = None

def init():
    global _firebase, _auth, _db, _storage
    if _firebase is None:
        missing = [k for k, v in _config.items() if not v and k not in ("measurementId",)]
        if missing:
            raise RuntimeError("Missing Firebase env vars: " + ", ".join(missing))
        _firebase = pyrebase.initialize_app(_config)
        _auth = _firebase.auth()
        _db = _firebase.database()
        _storage = _firebase.storage()
    return _firebase

def auth():
    init()
    return _auth

def db():
    init()
    return _db

def storage():
    init()
    return _storage
