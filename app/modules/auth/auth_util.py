import hashlib
import os
import string
import re
import openai
import requests
from cryptography.fernet import Fernet
from openai import OpenAI

from app import bcrypt, db
from flask_login import current_user
import random
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
    return UserAPIKey.query.filter_by(user_id=user_id, api_key_token=api_key_token).first()


def test_api_key_models(api_key, available_models):
    if "gpt-4" in available_models:
        test_result = test_gpt4(api_key)
    elif "gpt-3.5-turbo" in available_models:
        test_result = test_gpt3(api_key)
    else:
        return "Error"

    if test_result == "True":
        print(f"API Key: {api_key}, Available Models: {', '.join(available_models)}")
        return "gpt-4" if "gpt-4" in available_models else "gpt-3.5-turbo"
    elif test_result == "False":
        return "Error"
    return "Skip"


def get_unique_nickname(user_id, nickname):
    counter = 1
    original_nickname = nickname
    while UserAPIKey.query.filter_by(user_id=user_id, nickname=nickname).first():
        nickname = f"{original_nickname}({counter})"
        counter += 1
    return nickname


def create_and_save_api_key(user_id, api_key, nickname, label):
    api_key_identifier = api_key[:6]
    encrypted_api_key = encrypt_api_key(api_key)
    api_key_token = hash_api_key(api_key)
    new_key = UserAPIKey(
        user_id=user_id,
        encrypted_api_key=encrypted_api_key,
        nickname=nickname,
        identifier=api_key_identifier,
        api_key_token=api_key_token,
        label=label,
    )
    db.session.add(new_key)
    db.session.commit()
    return new_key


def initialize_openai_client(user_id):
    key_id = current_user.selected_api_key_id
    user_api_key = UserAPIKey.query.filter_by(user_id=user_id, id=key_id).first()

    if not user_api_key:
        return None, "API Key not found."

    api_key = decrypt_api_key(user_api_key.encrypted_api_key)
    client = OpenAI(api_key=api_key)
    return client, None
