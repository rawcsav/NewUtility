import openai
from flask import Blueprint, session, request

from app.util.docauth_util import check_api_key

bp = Blueprint('auth', __name__)


@bp.route('/set_api_key', methods=['POST'])
def set_api_key():
    api_key = request.form.get('api_key')

    # Validate the API key
    if not check_api_key(api_key):
        return "Invalid API Key", 400

    # If the key is valid, store it in the session and set it in the OpenAI library
    session['api_key'] = api_key
    openai.api_key = api_key

    return "API Key set successfully", 200


@bp.before_request
def set_openai_key_before_request():
    api_key = session.get('api_key')
    if api_key:
        openai.api_key = api_key
