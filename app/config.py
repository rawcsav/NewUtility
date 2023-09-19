import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

import tiktoken

SECRET_KEY = os.getenv("SECRET_KEY")
SESSION_TYPE = "filesystem"
SESSION_PERMANENT = True
PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Strict"
TEMPLATES_AUTO_RELOAD = True

TOKENIZER = tiktoken.get_encoding("cl100k_base")
EMBEDDING_MODEL = "text-embedding-ada-002"
GPT_MODEL = "gpt-4"
MAIN_TEMP_DIR = "app/main_user_directory"
MAX_LENGTH = 300
TOP_N = 4
BATCH_SIZE = 10
ALLOWED_EXTENSIONS = {"txt", "pdf", "docx"}

CLEANUP_THRESHOLD_SECONDS = 3600
SUPPORTED_FORMATS = (".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm")
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
INITIAL_PROMPT = "Hello, welcome to my lecture."
MAX_FILE_SIZE = 15 * 1024 * 1024
MAX_AUDIO_FILE_SIZE = 25 * 1024 * 1024
