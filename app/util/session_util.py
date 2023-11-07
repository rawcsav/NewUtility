import os
from datetime import timezone, timedelta, datetime
import openai
import sshtunnel
from cryptography.fernet import Fernet
from app import config
from flask_login import current_user


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

        # Initialize the OpenAI client with the decrypted API key
        client = openai.OpenAI(api_key=decrypted_api_key)
        return client
    else:
        raise Exception("No authenticated user")


def get_tunnel():
    tunnel = sshtunnel.SSHTunnelForwarder(
        (config.SSH_HOST),
        ssh_username=config.SSH_USER,
        ssh_password=config.SSH_PASS,
        remote_bind_address=(
            config.SQL_HOSTNAME, 3306)
    )
    tunnel.start()
    return tunnel
