import os
from datetime import timedelta

import tiktoken
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

SEARCH_ID = os.getenv("SEARCH_ID")
SEARCH_SECRET = os.getenv("SEARCH_SECRET")

AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
ME_URL = "https://api.spotify.com/v1/me"

SECRET_KEY = os.getenv("FLASK_SECRET_KEY")
FLASK_ENV = os.getenv("FLASK_ENV")

SESSION_TYPE = "sqlalchemy"
SESSION_PERMANENT = True
PERMANENT_SESSION_LIFETIME = timedelta(days=7)

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

SQL_ALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ECHO = False
SQLALCHEMY_POOL_RECYCLE = 299

SSH_HOST = os.getenv("SSH_HOST")
SSH_USER = os.getenv("SSH_USER")
SSH_PASS = os.getenv("SSH_PASS")
SQL_HOSTNAME = os.getenv("SQL_HOSTNAME")
SQL_USERNAME = os.getenv("SQL_USERNAME")
SQL_PASSWORD = os.getenv("SQL_PASSWORD")
SQL_DB_NAME = os.getenv("SQL_DB_NAME")

CLOUD_NAME = os.getenv("CLOUD_NAME")
CLOUD_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUD_SECRET = os.getenv("CLOUDINARY_SECRET")

TOKENIZER = tiktoken.get_encoding("cl100k_base")
EMBEDDING_MODEL = "text-embedding-ada-002"
MAIN_TEMP_DIR = "app/main_user_directory"
MAX_LENGTH = 250
TOP_N = 6
BATCH_SIZE = 10
ALLOWED_EXTENSIONS = {"txt", "pdf", "docx"}

CLEANUP_THRESHOLD_SECONDS = 3600
SUPPORTED_FORMATS = (".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm")
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
INITIAL_PROMPT = "Hello, welcome to my lecture."
MAX_FILE_SIZE = 15 * 1024 * 1024
MAX_AUDIO_FILE_SIZE = 25 * 1024 * 1024
