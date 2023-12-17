import openai
from flask import Blueprint, render_template, jsonify, Response
from flask_login import login_required, current_user
from openai import OpenAI

from app import db
from app.database import UserAPIKey, ChatPreferences, Conversation
from app.util.chat_util import chat_stream, chat_nonstream, save_message, \
    get_user_preferences, get_user_conversation
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

    if not conversation_history:
        new_conversation = Conversation(user_id=current_user.id,
                                        system_prompt=new_conversation_form.system_prompt.data)
        db.session.add(new_conversation)
        try:
            db.session.commit()
            conversation_history = [new_conversation]
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while creating a new conversation.', 'error')

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
        # Fetch all conversations for the user that start with "Convo #"
        existing_conversations = Conversation.query.filter(
            Conversation.user_id == user_id,
            Conversation.title.like("Convo #%")
        ).all()

        # Extract the numbers from the titles and find the maximum
        convo_numbers = [int(c.title.split('#')[-1]) for c in existing_conversations if
                         c.title.split('#')[-1].isdigit()]
        max_number = max(convo_numbers) if convo_numbers else 0

        # The title for the new conversation will be "Convo #{max_number + 1}"
        new_title = f"Convo #{max_number + 1}"

        # Create new conversation with the generated title
        new_conversation = Conversation(
            user_id=user_id,
            title=new_title,
            system_prompt=form.system_prompt.data
        )
        db.session.add(new_conversation)

        try:
            db.session.commit()
            # Get formatted creation date for the new conversation
            creation_date = new_conversation.created_at.strftime('%m/%d/%y')

            return jsonify({
                'status': 'success',
                'conversation_id': new_conversation.id,
                'title': new_conversation.title,
                'created_at': creation_date,
                'system_prompt': new_conversation.system_prompt
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'status': 'error', 'message': str(e)})
    else:
        return jsonify({'status': 'error', 'errors': form.errors})


@bp.route('/delete-conversation/<int:conversation_id>', methods=['POST'])
@login_required
def delete_conversation(conversation_id):
    conversation_to_delete = Conversation.query.get_or_404(conversation_id)
    if conversation_to_delete.user_id != current_user.id:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403

    # Check if this is the user's last conversation
    conversation_count = Conversation.query.filter_by(user_id=current_user.id).count()
    if conversation_count <= 1:
        return jsonify(
            {'status': 'error', 'message': 'Cannot have 0 conversations.'}), 403

    db.session.delete(conversation_to_delete)
    try:
        db.session.commit()
        return jsonify(
            {'status': 'success', 'message': 'Conversation deleted successfully.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)})


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


@bp.route('/conversation/<int:conversation_id>', methods=['GET'])
@login_required
def get_conversation_messages(conversation_id):
    conversation, conversation_history = get_user_conversation(current_user.id,
                                                               conversation_id)
    if conversation:
        messages = [
            {'content': message['content'], 'className': message['role'] + '-message'}
            for message in conversation_history]
        return jsonify({'messages': messages})
    else:
        return jsonify({'error': 'Conversation not found'}), 404


@bp.route('/update-conversation-title/<int:conversation_id>', methods=['POST'])
@login_required
def update_conversation_title(conversation_id):
    data = request.get_json()
    new_title = data.get('title')
    conversation = Conversation.query.get_or_404(conversation_id)

    if conversation.user_id != current_user.id:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403

    conversation.title = new_title
    try:
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Title updated successfully.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)})
