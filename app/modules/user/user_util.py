import os
from flask_login import current_user
from config import appdir

USER_DIRECTORY = os.path.join(appdir, "user_files")
if not os.path.exists(USER_DIRECTORY):
    os.makedirs(USER_DIRECTORY)


def ensure_directory_exists(directory_path):
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)


def get_user_gen_img_directory(user_id):
    directory = os.path.join(USER_DIRECTORY, str(user_id), "gen_img")
    ensure_directory_exists(directory)
    return directory


def get_user_chat_img_directory(user_id):
    directory = os.path.join(USER_DIRECTORY, str(user_id), "chat_img")
    ensure_directory_exists(directory)
    return directory


def get_user_upload_directory(user_id):
    directory = os.path.join(USER_DIRECTORY, str(user_id), "embed_docs")
    ensure_directory_exists(directory)
    return directory


def get_user_audio_directory(user_id):
    directory = os.path.join(USER_DIRECTORY, str(user_id), "audio_files")
    ensure_directory_exists(directory)
    return directory
