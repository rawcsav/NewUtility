import os
from datetime import timedelta

import tiktoken

if os.getenv('FLASK_ENV') == "development":
    from dotenv import load_dotenv

    load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

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

MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_DEFAULT_SENDER = "rawcsav@gmail.com"

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

GOOGLE_SITE_KEY = os.getenv("GOOGLE_SITE_KEY")
GOOGLE_SECRET_KEY = os.getenv("GOOGLE_SECRET_KEY")

TOKENIZER = tiktoken.get_encoding("cl100k_base")
EMBEDDING_MODEL = "text-embedding-ada-002"
MAIN_TEMP_DIR = "app/main_user_directory"
MAX_LENGTH = 250
TOP_N = 6
BATCH_SIZE = 10
ALLOWED_EXTENSIONS = {"txt", "pdf", "docx"}

CLEANUP_THRESHOLD_SECONDS = 3600
SUPPORTED_FORMATS = (".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm")
MAX_CONTENT_LENGTH = 50 * 1024 * 1024
INITIAL_PROMPT = "Hello, welcome to my lecture."
MAX_FILE_SIZE = 15 * 1024 * 1024
MAX_AUDIO_FILE_SIZE = 25 * 1024 * 1024

GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
GOOGLE_CALLBACK_URI = os.getenv("GOOGLE_CALLBACK_URI")
DEFAULT_USER_PASSWORD = os.getenv("DEFAULT_USER_PASSWORD")

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
GITHUB_CALLBACK_URI = os.getenv("GITHUB_CALLBACK_URI")
