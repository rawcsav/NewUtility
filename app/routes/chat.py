from datetime import datetime

from flask import jsonify, Response, abort
from flask import render_template, flash, request, stream_with_context, Blueprint
from flask_login import login_required, current_user
from openai import OpenAI

from app import db
from app.database import UserAPIKey, ChatPreferences, Conversation, Message
from app.util.chat_util import chat_stream, chat_nonstream, get_user_preferences, \
    user_history
from app.util.forms_util import ChatCompletionForm, UserPreferencesForm, \
    NewConversationForm
from app.util.session_util import decrypt_api_key

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
                    nonlocal full_response
                    conversation = Conversation.query.get(
                        conversation_id)  # Access the conversation object

                    for content in chat_stream(prompt, client, user_id,
                                               conversation_id):
                        full_response += content
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
    conversation, conversation_history = user_history(current_user.id, conversation_id)
    if conversation:
        messages = [
            {'content': message['content'], 'className': message['role'] + '-message',
             'messageId': message['id']}
            for message in conversation_history]

        # Update the last_checked_time for the conversation
        conversation.last_checked_time = datetime.utcnow()
        db.session.commit()

        return jsonify({'messages': messages})
    else:
        return jsonify({'error': 'Conversation not found'}), 404


@bp.route('/update-conversation-title/<int:conversation_id>', methods=['POST'])
@login_required
def update_conversation_title(conversation_id):
    data = request.get_json()
    new_title = data.get('title')

    # Validate new_title: not None, not just whitespace, and 25 characters or fewer
    if new_title is None or not new_title.strip() or len(new_title.strip()) > 25:
        return jsonify({
            'status': 'error',
            'message': 'Title must be provided, not just whitespace, and 25 characters or fewer.'
        }), 400

    conversation = Conversation.query.get_or_404(conversation_id)

    if conversation.user_id != current_user.id:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403

    # Update the conversation title with the validated and stripped title
    conversation.title = new_title.strip()
    try:
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Title updated successfully.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)})


@bp.route('/update-system-prompt/<int:conversation_id>', methods=['POST'])
@login_required
def update_system_prompt(conversation_id):
    data = request.get_json()
    new_system_prompt = data.get('system_prompt')

    # Check if new_system_prompt is not None, not just whitespace, and its length is less than 1000 characters
    if new_system_prompt.strip() is None or not new_system_prompt.strip() or len(
            new_system_prompt.strip()) >= 1000:
        return jsonify({
            'status': 'error',
            'message': 'System prompt must be provided, not just whitespace, and less than 1000 characters.'
        }), 400

    conversation = Conversation.query.get_or_404(conversation_id)

    if conversation.user_id != current_user.id:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403

    # Since we've already stripped the string for the check, it's a good idea to use the stripped version
    conversation.system_prompt = new_system_prompt.strip()
    try:
        db.session.commit()
        return jsonify(
            {'status': 'success', 'message': 'System prompt updated successfully.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)})


@bp.route('/edit-message/<int:message_id>', methods=['POST'])
@login_required
def edit_message(message_id):
    data = request.get_json()
    new_content = data.get('content')

    # Validate new_content: not None and not just whitespace
    if new_content is None or not new_content.strip():
        return jsonify({
            'status': 'error',
            'message': 'Content must be provided and not just whitespace.'
        }), 400

    message = Message.query.get_or_404(message_id)

    # Check if the current user is authorized to edit the message
    if message.conversation.user_id != current_user.id:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403

    # Update the message content with the validated and stripped content
    message.content = new_content.strip()
    try:
        db.session.commit()
        return jsonify(
            {'status': 'success', 'message': 'Message updated successfully.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)})


@bp.route('/check-new-messages/<int:conversation_id>', methods=['GET'])
@login_required
def check_new_messages(conversation_id):
    # Get the conversation from the database
    conversation = Conversation.query.get_or_404(conversation_id)

    # Get the last_checked_time from the conversation
    last_checked_time = conversation.last_checked_time

    # Query the database for new messages
    new_messages = Message.query.filter(
        Message.conversation_id == conversation_id,
        Message.created_at > last_checked_time
    ).all()

    # Convert the new messages to a list of dictionaries
    new_messages_dict = [{'id': message.id, 'content': message.content,
                          "className": "assistant-message" if message.direction == 'incoming' else "user-message",
                          'created_at': message.created_at.isoformat()} for message in
                         new_messages]

    return jsonify({'status': 'success', 'new_messages': new_messages_dict})


@bp.route('/retry-message/<int:message_id>', methods=['POST'])
@login_required
def retry_message(message_id):
    # Retrieve the message from the database
    message = Message.query.get_or_404(message_id)

    # Check if the current user is authorized to retry the message
    if message.conversation.user_id != current_user.id:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403

    # Resubmit the message content to the OpenAI API
    user_id = current_user.id
    conversation_id = message.conversation_id
    key_id = current_user.selected_api_key_id
    user_api_key = UserAPIKey.query.filter_by(user_id=user_id, id=key_id).first()

    if not user_api_key:
        return jsonify({'status': 'error', 'message': 'API Key not found.'})

    api_key = decrypt_api_key(user_api_key.encrypted_api_key)
    client = OpenAI(api_key=api_key)

    preferences = get_user_preferences(user_id)
    stream_preference = preferences.get('stream', True)
    prompt = message.content  # Use the content of the message being retried as the prompt
    try:
        if stream_preference:
            full_response = ""  # Initialize a variable to accumulate the full response

            def generate():
                nonlocal full_response  # Allow access to the full_response variable within the generator
                for content in chat_stream(prompt, client, user_id, conversation_id):
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
        Message.query.filter(Message.conversation_id == conversation_id,
                             Message.created_at > message.created_at).delete()
        db.session.commit()

        # Create a new message with the new completion from the OpenAI API
        new_message = Message(conversation_id=conversation_id, content=full_response,
                              direction='incoming')
        db.session.add(new_message)
        db.session.commit()

        return jsonify({'status': 'success', 'message': full_response})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


# An endpoint to signal interruption from the frontend
@bp.route('/interrupt-stream/<int:conversation_id>', methods=['POST'])
@login_required
def interrupt_stream(conversation_id):
    conversation = Conversation.query.get_or_404(conversation_id)
    if conversation.user_id != current_user.id:
        abort(403)  # HTTP 403 Forbidden

    # Log the current state before setting the flag
    print(f"Before setting interrupt: {conversation.is_interrupted}")

    conversation.is_interrupted = True
    db.session.commit()

    # Log the state after setting the flag
    print(f"After setting interrupt: {conversation.is_interrupted}")

    return jsonify({'status': 'success', 'message': 'Interruption signal received.'})
