import hashlib
import os
import random
import re

from flask_socketio import emit
from openai import OpenAI, AsyncOpenAI
import openai
import requests
from cryptography.fernet import Fernet
from flask_login import current_user
from app import db
from app.models.user_models import UserAPIKey, User


def generate_confirmation_code():
    return str(random.randint(100000, 999999))


def load_encryption_key():
    return os.environ["CRYPT_KEY"].encode()


def encrypt_api_key(api_key):
    cipher_suite = Fernet(load_encryption_key())
    encrypted_api_key = cipher_suite.encrypt(api_key.encode())
    return encrypted_api_key


def decrypt_api_key(encrypted_api_key):
    cipher_suite = Fernet(load_encryption_key())
    decrypted_api_key = cipher_suite.decrypt(encrypted_api_key)
    return decrypted_api_key.decode()


def hash_api_key(api_key):
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def check_available_models(api_key):
    headers = {"Authorization": f"Bearer {api_key}"}
    url = "https://api.openai.com/v1/models"

    response = requests.get(url, headers=headers)
    response_data = response.json()
    models = response_data.get("data", [])
    model_names = [model["id"] for model in models]
    return model_names


def test_gpt4(key):
    openai.api_key = key
    try:
        test = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello!"},
            ],
            max_tokens=1,
            temperature=0,
        )
        if test.choices[0].message.content:
            return "True"
    except openai.AuthenticationError as e:
        return "False"
    except openai.NotFoundError as e:
        return "False"
    except Exception:
        return "Skip"


def test_gpt3(key):
    openai.api_key = key
    try:
        test = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello!"},
            ],
            max_tokens=1,
            temperature=0,
        )
        if test.choices[0].message.content:
            return "True"
    except openai.AuthenticationError as e:
        return "False"
    except openai.NotFoundError as e:
        return "False"
    except Exception:
        return "Skip"


def is_valid_api_key_format(api_key):
    api_key_pattern = re.compile(r"sk-[A-Za-z0-9]{48}")
    return api_key_pattern.match(api_key)


def api_key_exists(user_id, api_key_token):
    return UserAPIKey.query.filter_by(user_id=user_id, api_key_token=api_key_token, delete=False).first()


def test_api_key_models(api_key, available_models):
    if "gpt-4" in available_models:
        test_result = test_gpt4(api_key)
    elif "gpt-3.5-turbo" in available_models:
        test_result = test_gpt3(api_key)
    else:
        return "Error"

    if test_result == "True":
        return "gpt-4" if "gpt-4" in available_models else "gpt-3.5-turbo"
    elif test_result == "False":
        return "Error"
    return "Skip"


def get_unique_nickname(user_id, nickname):
    counter = 1
    original_nickname = nickname
    while UserAPIKey.query.filter_by(user_id=user_id, nickname=nickname, delete=False).first():
        nickname = f"{original_nickname}({counter})"
        counter += 1
    return nickname


def create_and_save_api_key(user_id, api_key, nickname, label):
    # Encrypt and hash the API key
    api_key_identifier = api_key[:6]
    encrypted_api_key = encrypt_api_key(api_key)
    api_key_token = hash_api_key(api_key)

    # Create the API key object
    new_key = UserAPIKey(
        user_id=user_id,
        encrypted_api_key=encrypted_api_key,
        nickname=nickname,
        identifier=api_key_identifier,
        api_key_token=api_key_token,
        label=label,
    )

    # Add to the session
    db.session.add(new_key)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e  # Handle or log the exception appropriately
    existing_keys_count = UserAPIKey.query.filter_by(user_id=user_id, delete=False).count()
    if existing_keys_count == 1:
        current_user.selected_api_key_id = new_key.id
        db.session.commit()

    return new_key


def initialize_openai_client(user_id):
    key_id = current_user.selected_api_key_id
    user_api_key = UserAPIKey.query.filter_by(user_id=user_id, id=key_id, delete=False).first()

    if not user_api_key:
        return None, "API Key not found."

    api_key = decrypt_api_key(user_api_key.encrypted_api_key)
    client = OpenAI(api_key=api_key, max_retries=5, timeout=30.0)
    return client, None


def task_client(session, user_id, max_retries=3, timeout=15):
    user = session.query(User).filter_by(id=user_id).first()
    key_id = user.selected_api_key_id
    user_api_key = session.query(UserAPIKey).filter_by(user_id=user_id, id=key_id, delete=False).first()
    if not user_api_key:
        return None, "API Key not found."
    api_key = decrypt_api_key(user_api_key.encrypted_api_key)
    client = OpenAI(api_key=api_key, max_retries=max_retries, timeout=timeout)
    return client, key_id, None

def task_async_client(session, user_id):
    user = session.query(User).filter_by(id=user_id).first()
    key_id = user.selected_api_key_id
    user_api_key = session.query(UserAPIKey).filter_by(user_id=user_id, id=key_id, delete=False).first()
    if not user_api_key:
        return None, "API Key not found."
    api_key = decrypt_api_key(user_api_key.encrypted_api_key)
    client = AsyncOpenAI(api_key=api_key, max_retries=5, timeout=30.0)
    return client, key_id, None

from functools import wraps
from flask import redirect, url_for, jsonify, flash
from flask_login import current_user


def requires_selected_api_key(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not current_user.selected_api_key_id:
            flash("Please select an API key.", "warning")
            return redirect(url_for("user_bp.dashboard"))
        return func(*args, **kwargs)
    return decorated_function


def requires_unlimited_api_key(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not current_user.selected_api_key_id:
            return redirect(url_for("user_bp.dashboard"))

        user_api_key = UserAPIKey.query.filter_by(user_id=current_user.id, id=current_user.selected_api_key_id,
                                                  delete=False).first()
        if user_api_key.label != "gpt-4":
            return jsonify({"status": "error", "message": "Access denied. Your API key has limited access."}), 403

        return func(*args, **kwargs)

    return decorated_function



