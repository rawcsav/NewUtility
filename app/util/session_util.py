import os
import string
from datetime import timezone, timedelta, datetime
import openai
import requests
import sshtunnel
from cryptography.fernet import Fernet
from app import config, bcrypt
from flask_login import current_user
import random

from app.database import UserAPIKey, db, User


def generate_confirmation_code():
    return str(random.randint(100000, 999999))  # 6-digit code


def load_encryption_key():
    return os.environ['CRYPT_KEY'].encode()


def encrypt_api_key(api_key):
    cipher_suite = Fernet(load_encryption_key())
    encrypted_api_key = cipher_suite.encrypt(api_key.encode())
    return encrypted_api_key.decode()


def decrypt_api_key(encrypted_api_key):
    cipher_suite = Fernet(load_encryption_key())
    decrypted_api_key = cipher_suite.decrypt(encrypted_api_key.encode())
    return decrypted_api_key.decode()


def is_api_key_valid(api_key):
    openai.api_key = api_key
    try:
        openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello!"}
            ]
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


def get_openai_client():
    if current_user.is_authenticated:
        encrypted_api_key = current_user.selected_api_key.encrypted_api_key
        decrypted_api_key = decrypt_api_key(
            encrypted_api_key)  # Implement this decryption function

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
        if test.choices[0].message.content:
            print(f"Key is valid for GPT-4: {key}")
        else:
            print(f"Key failed with status code: {key}")
    except openai.OpenAIError as e:
        print(f"OpenAI error: {e}")


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
            print(f"Key is valid for GPT-3.5: {key}")
        else:
            print(f"Key failed with status code: {key}")
    except openai.OpenAIError as e:
        print(f"OpenAI error: {e}")


def test_dalle3_key(key):
    openai.api_key = key
    try:
        response_dalle3 = openai.images.generate(
            model="dall-e-3",  # Replace with the actual model identifier for DALL-E 3
            prompt="a white siamese cat",
            size="1024x1024",
            n=1,
        )
        image_url = response_dalle3.data[0].url
        if image_url:
            print(f"Working DALL-E 3 Key: {key}")
        else:
            print(f"Key failed with status code: {key}")
    except openai.OpenAIError as e:
        print(f"OpenAI error: {e}")


def random_string(length=5):
    """Generate a random string of fixed length."""
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))


# Helper function for reCAPTCHA verification
def verify_recaptcha(recaptcha_response):
    if not recaptcha_response:
        return {'status': 'error',
                'message': 'reCAPTCHA verification failed. Please try again.'}, 400

    recaptcha_secret = config.GOOGLE_SECRET_KEY
    recaptcha_data = {'secret': recaptcha_secret, 'response': recaptcha_response}
    recaptcha_request = requests.post('https://www.google.com/recaptcha/api/siteverify',
                                      data=recaptcha_data)
    recaptcha_result = recaptcha_request.json()

    if not recaptcha_result.get('success'):
        return {'status': 'error',
                'message': 'reCAPTCHA verification failed. Please try again.'}, 400

    return None  # No error


# Helper function to create or update a user from OAuth information
def get_or_create_user(email, username, login_method):
    user = User.query.filter_by(email=email).first()
    if not user:
        while User.query.filter_by(username=username).first():
            username = f"{username}_{random_string(5)}"
        user = User(
            email=email,
            username=username,
            email_confirmed=True,
            password_hash=bcrypt.generate_password_hash(
                config.DEFAULT_USER_PASSWORD).decode('utf-8'),
            login_method=login_method
        )
        db.session.add(user)
        db.session.commit()
    else:
        user.login_method = login_method
        db.session.commit()
    return user
