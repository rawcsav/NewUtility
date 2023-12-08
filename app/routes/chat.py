import openai
from flask import Blueprint, render_template, jsonify
from flask import render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from openai import OpenAI

from app import db
from app.database import UserAPIKey, ChatPreferences, Conversation
from app.util.chat_utils import chat_stream, chat_nonstream, save_message, \
    get_user_preferences
from app.util.forms_util import ChatCompletionForm, UserPreferencesForm, \
    NewConversationForm
from app.util.session_util import decrypt_api_key
from flask import Blueprint, request, render_template, flash, redirect, url_for
from flask_login import login_required, current_user

bp = Blueprint('chat', __name__, url_prefix='/chat')


@bp.route('/', methods=['GET'])
@login_required
def chat_index():
    # This route will just render the chat_page.html template
    # and provide the necessary form instances for the template to use.
    new_conversation_form = NewConversationForm()
    user_preferences_form = UserPreferencesForm()
    chat_completion_form = ChatCompletionForm()

    return render_template('chat_page.html',
                           new_conversation_form=new_conversation_form,
                           user_preferences_form=user_preferences_form,
                           chat_completion_form=chat_completion_form)


@bp.route('/new-conversation', methods=['POST'])
@login_required
def new_conversation():
    form = NewConversationForm()
    if form.validate_on_submit():
        user_id = current_user.id
        system_prompt = form.system_prompt.data
        new_conversation = Conversation(user_id=user_id, system_prompt=system_prompt)
        db.session.add(new_conversation)
        try:
            db.session.commit()
            return jsonify(
                {'status': 'success', 'conversation_id': new_conversation.id})
        except Exception as e:
            db.session.rollback()
            return jsonify({'status': 'error', 'message': str(e)})
    else:
        return jsonify({'status': 'error', 'errors': form.errors})


@bp.route('/update-preferences', methods=['POST'])
@login_required
def update_preferences():
    form = UserPreferencesForm()
    if form.validate_on_submit():
        user_id = current_user.id
        preferences = ChatPreferences.query.filter_by(user_id=user_id).first_or_404()

        preferences.show_timestamps = form.show_timestamps.data
        preferences.model = form.model.data
        preferences.temperature = form.temperature.data
        preferences.max_tokens = form.max_tokens.data
        preferences.frequency_penalty = form.frequency_penalty.data
        preferences.presence_penalty = form.presence_penalty.data
        preferences.top_p = form.top_p.data
        preferences.stream = form.stream.data

        try:
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Preferences updated.'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'status': 'error', 'message': str(e)})
    else:
        return jsonify({'status': 'error', 'errors': form.errors})


@bp.route('/completion', methods=['POST'])
@login_required
def chat_completion():
    form = ChatCompletionForm()
    if form.validate_on_submit():
        user_id = current_user.id
        conversation_id = form.conversation_id.data
        key_id = current_user.selected_api_key_id
        user_api_key = UserAPIKey.query.filter_by(user_id=user_id, id=key_id).first()

        if not user_api_key:
            return jsonify({'status': 'error', 'message': 'API Key not found.'})

        api_key = decrypt_api_key(user_api_key.encrypted_api_key)
        client = OpenAI(api_key=api_key)

        preferences = get_user_preferences(user_id)
        stream_preference = preferences.get('stream', True)

        prompt = form.prompt.data
        save_message(conversation_id, prompt, 'incoming', preferences['model'])

        try:
            if stream_preference:
                full_response = chat_stream(prompt, client, user_id, conversation_id)
            else:
                full_response = chat_nonstream(prompt, client, user_id, conversation_id)

            if full_response:
                save_message(conversation_id, full_response, 'outgoing',
                             preferences['model'])
                return jsonify(
                    {'status': 'success', 'message': 'Chat completed successfully.'})
            else:
                return jsonify(
                    {'status': 'warning', 'message': 'No response from the AI.'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)})
    else:
        return jsonify({'status': 'error', 'errors': form.errors})
