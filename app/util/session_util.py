import hashlib
import os
import string
from typing import re

import openai
import requests
from cryptography.fernet import Fernet
from flask import jsonify

from app import bcrypt, db
from flask_login import current_user
import random
from app.database import User


def generate_confirmation_code():
    return str(random.randint(100000, 999999))


def load_encryption_key():
    return os.environ['CRYPT_KEY'].encode()


def encrypt_api_key(api_key):
    cipher_suite = Fernet(load_encryption_key())
    encrypted_api_key = cipher_suite.encrypt(api_key.encode())
    return encrypted_api_key


def decrypt_api_key(encrypted_api_key):
    cipher_suite = Fernet(load_encryption_key())
    decrypted_api_key = cipher_suite.decrypt(
        encrypted_api_key)
    return decrypted_api_key.decode()


def hash_api_key(api_key):
    return hashlib.sha256(api_key.encode('utf-8')).hexdigest()


def is_api_key_valid(api_key):
    openai.api_key = api_key
    try:
        openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello!"}
            ],
            max_tokens=5,
            temperature=0,
        )
    except openai.APIConnectionError as e:
        print(f"Invalid request: {e}")
        return False
    except openai.APIStatusError as e:
        print(f"OpenAI error: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False
    else:
        return True


def check_dalle3(api_key):
    openai.api_key = api_key

    try:
        # Setting the API key for the session

        # Attempt to generate an image
        openai.images.generate(
            model="dall-e-3",
            prompt="""test""",
            size="1024x1024",
            quality="standard",
            style="vivid",
            n=1)

    except openai.APIConnectionError as e:
        print(f"Invalid request: {e}")
        return False
    except openai.APIStatusError as e:
        print(f"OpenAI error: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False
    else:
        return True


def get_openai_client():
    if current_user.is_authenticated:
        encrypted_api_key = current_user.selected_api_key.encrypted_api_key
        decrypted_api_key = decrypt_api_key(
            encrypted_api_key)

        client = openai.OpenAI(api_key=decrypted_api_key)
        return client
    else:
        raise Exception("No authenticated user")


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
                {"role": "user", "content": "Hello!"}
            ],
            max_tokens=10,
            temperature=0,
        )
    except openai.APIConnectionError as e:
        print(f"Invalid request: {e}")
        return False
    except openai.APIStatusError as e:
        print(f"OpenAI error: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False
    else:
        return True


def test_gpt3(key):
    openai.api_key = key
    try:
        test = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello!"}
            ],
            max_tokens=10,
            temperature=0,
        )
        if test.choices[0].message.content:
            return True
    except openai.OpenAIError:
        return False


def random_string(length=5):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))


def verify_recaptcha(recaptcha_secret, recaptcha_response):
    if not recaptcha_response:
        return {'status': 'error',
                'message': 'reCAPTCHA verification failed. Please try again.'}, 400

    recaptcha_data = {'secret': recaptcha_secret, 'response': recaptcha_response}
    recaptcha_request = requests.post('https://www.google.com/recaptcha/api/siteverify',
                                      data=recaptcha_data)
    recaptcha_result = recaptcha_request.json()

    if not recaptcha_result.get('success'):
        return {'status': 'error',
                'message': 'reCAPTCHA verification failed. Please try again.'}, 400

    return None


def get_or_create_user(email, username, login_method, default_user_password):
    user = User.query.filter_by(email=email).first()
    if not user:
        while User.query.filter_by(username=username).first():
            username = f"{username}_{random_string(5)}"
        user = User(
            email=email,
            username=username,
            email_confirmed=True,
            password_hash=bcrypt.generate_password_hash(default_user_password).decode(
                'utf-8'),
            login_method=login_method
        )
        db.session.add(user)
        db.session.commit()
    else:
        user.login_method = login_method
        db.session.commit()
    return user


def authenticate_user(request_user_id, current_user_id):
    if request_user_id != current_user_id:
        return False, jsonify({'status': 'error', 'message': 'Unauthorized access.'})
    return True, None


def generate_unique_username(base_username):
    sanitized_username = re.sub(r'\W+', '', base_username)

    new_username = sanitized_username
    counter = 1
    while User.query.filter_by(username=new_username).first():
        new_username = f"{sanitized_username}{counter}"
        counter += 1

    return new_username
