import openai
from flask import Blueprint, render_template
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

bp = Blueprint('chat', __name__, url_prefix='/chat')


@bp.route('/new-conversation', methods=['GET', 'POST'])
@login_required
def new_conversation():
    form = NewConversationForm()
    if form.validate_on_submit():
        user_id = current_user.id
        system_prompt = form.system_prompt.data

        # Create a new conversation entry
        new_conversation = Conversation(user_id=user_id, system_prompt=system_prompt)
        db.session.add(new_conversation)
        try:
            db.session.commit()
            flash('New conversation started.', 'success')
            return redirect(
                url_for('chat.chat_completion', conversation_id=new_conversation.id))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while starting a new conversation: {e}', 'danger')

    return render_template('chat/new_conversation.html', form=form)


@bp.route('/update-preferences', methods=['GET', 'POST'])
@login_required
def update_preferences():
    user_id = current_user.id
    preferences = ChatPreferences.query.filter_by(user_id=user_id).first_or_404()

    form = UserPreferencesForm(obj=preferences)

    if form.validate_on_submit():
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
            flash('Your preferences have been updated.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {e}', 'danger')

        return redirect(url_for('chat.update_preferences'))

    return render_template('chat/update_preferences.html', form=form)


@bp.route('/completion', methods=['GET', 'POST'])
@login_required
def chat_completion():
    form = ChatCompletionForm()
    if form.validate_on_submit():
        user_id = current_user.id
        conversation_id = form.conversation_id.data

        key_id = current_user.selected_api_key_id
        user_api_key = UserAPIKey.query.filter_by(user_id=user_id, id=key_id).first()
        if not user_api_key:
            flash('API Key not found.', 'danger')
            return redirect(
                url_for('your_redirect_endpoint'))

        api_key = decrypt_api_key(user_api_key.encrypted_api_key)
        client = openai.OpenAI(api_key=api_key)

        preferences = get_user_preferences(user_id)
        stream_preference = preferences.get('stream',
                                            True)

        prompt = form.prompt.data

        save_message(conversation_id, prompt, 'incoming', preferences['model'])

        try:
            full_response = ""
            if stream_preference:
                full_response = chat_stream(prompt, client, user_id, conversation_id)
            else:
                full_response = chat_nonstream(prompt, client, user_id, conversation_id)

            if full_response:
                save_message(conversation_id, full_response, 'outgoing',
                             preferences['model'])
                flash('Chat completed successfully.', 'success')
            else:
                flash('No response from the AI.', 'warning')
        except Exception as e:
            flash(f'An error occurred: {e}', 'danger')

        return redirect(url_for('your_redirect_endpoint'))

    return redirect(url_for('your_redirect_endpoint'))
