import os
from datetime import timedelta
import tiktoken

# Environment and Debug Configuration
FLASK_ENV = os.getenv("FLASK_ENV")
SECRET_KEY = os.getenv("FLASK_SECRET_KEY")

# Session Configuration
SESSION_PERMANENT = True
PERMANENT_SESSION_LIFETIME = timedelta(days=30)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

# Login Configuration
REMEMBER_COOKIE_SECURE = True
REMEMBER_COOKIE_HTTPONLY = True
REMEMBER_COOKIE_DURATION = timedelta(days=30)

# Database Configuration
SQL_ALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ECHO = False
SQLALCHEMY_POOL_RECYCLE = 299
SQL_HOSTNAME = os.getenv("SQL_HOSTNAME")
SQL_USERNAME = os.getenv("SQL_USERNAME")
SQL_PASSWORD = os.getenv("SQL_PASSWORD")
SQL_DB_NAME = os.getenv("SQL_DB_NAME")

# Mail Configuration
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_DEFAULT_SENDER = "rawcsav@gmail.com"

# SSH Configuration
SSH_HOST = os.getenv("SSH_HOST")
SSH_USER = os.getenv("SSH_USER")
SSH_PASS = os.getenv("SSH_PASS")

# Cloudinary Configuration
CLOUD_NAME = os.getenv("CLOUD_NAME")
CLOUD_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUD_SECRET = os.getenv("CLOUDINARY_SECRET")

# Google Configuration
GOOGLE_SITE_KEY = os.getenv("GOOGLE_SITE_KEY")
GOOGLE_SECRET_KEY = os.getenv("GOOGLE_SECRET_KEY")
GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
GOOGLE_CALLBACK_URI = os.getenv("GOOGLE_CALLBACK_URI")

# GitHub Configuration
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
GITHUB_CALLBACK_URI = os.getenv("GITHUB_CALLBACK_URI")

# User Configuration
DEFAULT_USER_PASSWORD = os.getenv("DEFAULT_USER_PASSWORD")

# Tokenizer and Model Configuration
TOKENIZER = tiktoken.get_encoding("cl100k_base")
EMBEDDING_MODEL = "text-embedding-ada-002"

# Directory and File Configuration
MAIN_TEMP_DIR = "app/main_user_directory"
ALLOWED_EXTENSIONS = {"txt", "pdf", "docx"}
SUPPORTED_FORMATS = (".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm")

# Uploads Configuration
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB
MAX_FILE_SIZE = 15 * 1024 * 1024  # 15 MB
MAX_AUDIO_FILE_SIZE = 25 * 1024 * 1024  # 25 MB

# Prompt and Text Configuration
INITIAL_PROMPT = "Hello, welcome to my lecture."
MAX_LENGTH = 250
TOP_N = 6
BATCH_SIZE = 10

# Cleanup Configuration
CLEANUP_THRESHOLD_SECONDS = 3600
