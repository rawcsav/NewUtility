import openai
from flask import Blueprint, render_template, jsonify, Response
from flask_login import login_required, current_user
from openai import OpenAI

from app import db
from app.database import UserAPIKey, ChatPreferences, Conversation
from app.util.chat_util import chat_stream, chat_nonstream, save_message, \
    get_user_preferences
from app.util.forms_util import ChatCompletionForm, UserPreferencesForm, \
    NewConversationForm
from app.util.session_util import decrypt_api_key
from flask import Blueprint, request, render_template, flash, redirect, url_for, \
    session, request, stream_with_context, Blueprint, current_app
from flask_login import login_required, current_user

bp = Blueprint('chat', __name__, url_prefix='/chat')

from sqlalchemy.inspection import inspect


def model_to_dict(model):
    return {c.key: getattr(model, c.key)
            for c in inspect(model).mapper.column_attrs}


@bp.route('/', methods=['GET'])
@login_required
def chat_index():
    # Create form instances
    new_conversation_form = NewConversationForm()
    chat_completion_form = ChatCompletionForm()

    # Retrieve the user's conversation history
    conversation_history = Conversation.query.filter_by(user_id=current_user.id).all()

    # If no conversation history exists for the user, create a new conversation
    if not conversation_history:
        # Define a default system prompt similar to ChatGPT's web interface
        default_system_prompt = "Hello! How can I assist you today?"
        new_conversation = Conversation(user_id=current_user.id,
                                        system_prompt=default_system_prompt)
        db.session.add(new_conversation)
        try:
            db.session.commit()
            # Reload the conversation history after creating the new conversation
            conversation_history = [new_conversation]
        except Exception as e:
            db.session.rollback()
            # Handle the exception by logging and flashing an error message to the user
            current_app.logger.error(f'Error creating a new conversation: {e}')
            flash('An error occurred while creating a new conversation.', 'error')
            # Optionally, you may choose to redirect the user or perform other error-handling steps here.

    # Try to get the existing preferences or create a new instance if they don't exist
    preferences = ChatPreferences.query.filter_by(user_id=current_user.id).first()
    if not preferences:
        preferences = ChatPreferences(user_id=current_user.id)
        db.session.add(preferences)
        db.session.commit()

    conversation_history_data = [
        {
            'id': conversation.id,
            'title': conversation.title,
            'created_at': conversation.created_at,
            'system_prompt': conversation.system_prompt,
            # Add other fields as necessary
        }
        for conversation in conversation_history
    ]
    preferences_dict = model_to_dict(preferences)
    user_preferences_form = UserPreferencesForm(data=preferences_dict)

    # Pass the conversation history and other form instances to the template
    return render_template('chat_page.html',
                           new_conversation_form=new_conversation_form,
                           user_preferences_form=user_preferences_form,
                           chat_completion_form=chat_completion_form,
                           conversation_history=conversation_history_data)


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
            print(new_conversation.id)
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
        preferences = ChatPreferences.query.filter_by(user_id=current_user.id).first()
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
            return jsonify(
                {'status': 'success', 'message': 'Preferences updated successfully.'})
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
        if not conversation_id or not Conversation.query.get(conversation_id):
            return jsonify({'status': 'error', 'message': 'Invalid conversation ID.'})
        key_id = current_user.selected_api_key_id
        user_api_key = UserAPIKey.query.filter_by(user_id=user_id, id=key_id).first()

        if not user_api_key:
            return jsonify({'status': 'error', 'message': 'API Key not found.'})

        api_key = decrypt_api_key(user_api_key.encrypted_api_key)
        client = OpenAI(api_key=api_key)

        preferences = get_user_preferences(user_id)
        stream_preference = preferences.get('stream', True)
        prompt = form.prompt.data

        try:
            if stream_preference:
                full_response = ""  # Initialize a variable to accumulate the full response

                def generate():
                    nonlocal full_response  # Allow access to the full_response variable within the generator
                    for content in chat_stream(prompt, client, user_id,
                                               conversation_id):
                        full_response += content  # Accumulate the content
                        yield content

                # Create a response object that streams the content
                response = Response(
                    stream_with_context(generate()),
                    content_type="text/plain"
                )
                response.headers["X-Accel-Buffering"] = "no"
                return response
            else:
                full_response = chat_nonstream(prompt, client, user_id, conversation_id)
                if full_response:
                    return jsonify(
                        {'status': 'success',
                         'message': full_response.strip()})
                else:
                    return jsonify(
                        {'status': 'warning', 'message': 'No response from the AI.'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)})
    else:
        return jsonify({'status': 'error', 'errors': form.errors})
