import os
from datetime import datetime

from flask import jsonify, Response, abort, session, current_app, send_from_directory
from flask import render_template, flash, request, Blueprint
from flask_login import login_required, current_user
from markdown2 import markdown
from sqlalchemy.inspection import inspect
from app.modules.auth.auth_util import requires_selected_api_key
from app import db
from app.models.embedding_models import Document
from app.models.chat_models import Conversation, Message, ChatPreferences
from app.modules.chat.chat_util import (
    get_user_preferences,
    get_user_history,
    handle_stream,
    retry_delete_messages,
    set_interruption_flag,
)
from app.modules.embedding.embedding_util import append_knowledge_context
from app.utils.forms_util import ChatCompletionForm, UserPreferencesForm, NewConversationForm, UpdateDocPreferencesForm
from app.modules.auth.auth_util import initialize_openai_client
from app.utils.vector_cache import VectorCache

chat_bp = Blueprint("chat_bp", __name__, template_folder="templates", static_folder="static", url_prefix="/chat")


def model_to_dict(model):
    return {c.key: getattr(model, c.key) for c in inspect(model).mapper.column_attrs}


@chat_bp.route("/", methods=["GET"])
@requires_selected_api_key
@login_required
def chat_index():
    new_conversation_form = NewConversationForm()
    chat_completion_form = ChatCompletionForm()
    markdown_file_path = os.path.join(current_app.root_path, chat_bp.static_folder, "chat.md")

    with open(markdown_file_path, "r") as file:
        markdown_content = file.read()
    docs_content = markdown(markdown_content)

    conversation_history = Conversation.query.filter_by(user_id=current_user.id, delete=False).all()

    if not conversation_history:
        new_conversation = Conversation(user_id=current_user.id, system_prompt=new_conversation_form.system_prompt.data)
        db.session.add(new_conversation)
        try:
            db.session.commit()
            conversation_history = [new_conversation]
        except Exception:
            db.session.rollback()
            flash("An error occurred while creating a new conversation.", "error")

    preferences = ChatPreferences.query.filter_by(user_id=current_user.id).first()
    if not preferences:
        preferences = ChatPreferences(user_id=current_user.id)
        db.session.add(preferences)
        db.session.commit()

    conversation_history_data = [
        {
            "id": conversation.id,
            "title": conversation.title,
            "created_at": conversation.created_at,
            "system_prompt": conversation.system_prompt,
        }
        for conversation in conversation_history
    ]
    preferences_dict = model_to_dict(preferences)
    user_preferences_form = UserPreferencesForm(data=preferences_dict)

    user_documents = Document.query.filter_by(user_id=current_user.id, delete=False).all()
    documents_data = [
        {
            "id": doc.id,
            "title": doc.title,
            "author": doc.author,
            "total_tokens": doc.total_tokens,
            "chunk_count": len(doc.chunks),
            "selected": doc.selected,
        }
        for doc in user_documents
    ]
    if preferences.knowledge_query_mode:
        VectorCache.load_user_vectors(current_user.id)
    return render_template(
        "chat_page.html",
        new_conversation_form=new_conversation_form,
        user_preferences_form=user_preferences_form,
        chat_completion_form=chat_completion_form,
        conversation_history=conversation_history_data,
        documents=documents_data,
        preferences_dict=preferences_dict,
        doc_preferences_form=UpdateDocPreferencesForm(data=preferences_dict),
    )


@chat_bp.route("/new-conversation", methods=["POST"])
@requires_selected_api_key
@login_required
def new_conversation():
    form = NewConversationForm()
    if form.validate_on_submit():
        user_id = current_user.id
        conversation_count = Conversation.query.filter_by(user_id=user_id, delete=False).count()
        if conversation_count >= 5:
            return jsonify({"status": "error", "message": "Maximum number of conversations reached"})

        # Fetch all conversations for the user that start with "Convo #"
        existing_conversations = Conversation.query.filter(
            Conversation.user_id == user_id, Conversation.title.like("Convo #%"), Conversation.delete == False
        ).all()

        convo_numbers = [
            int(c.title.split("#")[-1]) for c in existing_conversations if c.title.split("#")[-1].isdigit()
        ]
        max_number = max(convo_numbers) if convo_numbers else 0

        new_title = f"Convo #{max_number + 1}"

        new_conversation = Conversation(
            user_id=user_id, title=new_title, system_prompt=form.system_prompt.data, last_checked_time=datetime.utcnow()
        )
        db.session.add(new_conversation)

        try:
            db.session.commit()
            creation_date = new_conversation.created_at.strftime("%m/%d/%y")

            return jsonify(
                {
                    "status": "success",
                    "conversation_id": new_conversation.id,
                    "title": new_conversation.title,
                    "created_at": creation_date,
                    "system_prompt": new_conversation.system_prompt,
                }
            )
        except Exception as e:
            db.session.rollback()
            return jsonify({"status": "error", "message": str(e)})
    else:
        return jsonify({"status": "error", "errors": form.errors})


@chat_bp.route("/delete-conversation/<string:conversation_id>", methods=["POST"])
@requires_selected_api_key
@login_required
def delete_conversation(conversation_id):
    conversation_to_delete = Conversation.query.get_or_404(conversation_id)
    if conversation_to_delete.user_id != current_user.id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    # Check if this is the user's last conversation
    conversation_count = Conversation.query.filter_by(user_id=current_user.id, delete=False).count()
    if conversation_count <= 1:
        return jsonify({"status": "error", "message": "Cannot have 0 conversations."}), 403

    conversation_to_delete.delete = True
    try:
        db.session.commit()
        return jsonify({"status": "success", "message": "Conversation deleted successfully."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)})


@chat_bp.route("/update-preferences", methods=["POST"])
@requires_selected_api_key
@login_required
def update_preferences():
    form = UserPreferencesForm()
    if form.validate_on_submit():
        preferences = ChatPreferences.query.filter_by(user_id=current_user.id).first()
        old_model = preferences.model
        preferences.model = form.model.data
        preferences.temperature = form.temperature.data
        preferences.max_tokens = form.max_tokens.data
        preferences.frequency_penalty = form.frequency_penalty.data
        preferences.presence_penalty = form.presence_penalty.data
        preferences.top_p = form.top_p.data

        try:
            db.session.commit()
            return jsonify({"status": "success", "message": "Preferences updated successfully."})
        except Exception as e:
            db.session.rollback()
            return jsonify({"status": "error", "message": str(e)})


@chat_bp.route("/completion", methods=["POST"])
@requires_selected_api_key
@login_required
def chat_completion():
    form = ChatCompletionForm()
    if not form.validate_on_submit():
        return jsonify({"status": "error", "errors": form.errors})

    user_id = current_user.id
    conversation_id = form.conversation_id.data
    if not conversation_id or not Conversation.query.get(conversation_id):
        return jsonify({"status": "error", "message": "Invalid conversation ID."})

    client, error = initialize_openai_client(user_id)
    if error:
        return jsonify({"status": "error", "message": error})

    preferences = get_user_preferences(user_id)
    raw_prompt = form.prompt.data
    try:
        result = append_knowledge_context(raw_prompt, user_id, client)
        if isinstance(result, tuple):
            prompt, chunk_associations = result if len(result) == 2 else (result[0], None)
        else:
            prompt, chunk_associations = result, None
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    session["interruption"] = None
    try:
        response, _ = handle_stream(
            raw_prompt, prompt, client, user_id, conversation_id, chunk_associations=chunk_associations
        )
        return Response(response, content_type="text/event-stream", headers={"X-Accel-Buffering": "no"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@chat_bp.route("/retry-message/<string:message_id>", methods=["POST"])
@requires_selected_api_key
@login_required
def retry_message(message_id):
    message = Message.query.get_or_404(message_id)
    conversation_id = message.conversation_id

    if message.conversation.user_id != current_user.id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    user_id = current_user.id
    client, error = initialize_openai_client(user_id)
    if error:
        return jsonify({"status": "error", "message": error})

    raw_prompt = message.content
    try:
        result = append_knowledge_context(raw_prompt, user_id, client)
        if isinstance(result, tuple):
            prompt, chunk_associations = result if len(result) == 2 else (result[0], None)
        else:
            prompt, chunk_associations = result, None
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    session["interruption"] = None
    try:
        retry_delete_messages(conversation_id, message.id)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    try:
        response, _ = handle_stream(
            raw_prompt, prompt, client, user_id, conversation_id, retry=True, chunk_associations=chunk_associations
        )
        return Response(response, content_type="text/event-stream", headers={"X-Accel-Buffering": "no"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@chat_bp.route("/conversation/<string:conversation_id>", methods=["GET"])
@requires_selected_api_key
@login_required
def get_conversation_messages(conversation_id):
    conversation, conversation_history = get_user_history(current_user.id, conversation_id)
    if conversation:
        messages = [
            {"content": message["content"], "className": message["role"] + "-message", "messageId": message["id"]}
            for message in conversation_history
        ]
        conversation.last_checked_time = datetime.utcnow()
        db.session.commit()
        return jsonify({"messages": messages})
    else:
        return jsonify({"error": "Conversation not found"}), 404


@chat_bp.route("/update-conversation-title/<string:conversation_id>", methods=["POST"])
@requires_selected_api_key
@login_required
def update_conversation_title(conversation_id):
    data = request.get_json()
    new_title = data.get("title")

    if new_title is None or not new_title.strip() or len(new_title.strip()) > 25:
        return jsonify({"status": "error", "message": "Title must be provided (25 characters or fewer)."}), 400

    conversation = Conversation.query.get_or_404(conversation_id)

    if conversation.user_id != current_user.id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    # Update the conversation title with the validated and stripped title
    conversation.title = new_title.strip()
    try:
        db.session.commit()
        return jsonify({"status": "success", "message": "Title updated successfully."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)})


@chat_bp.route("/conversation/<string:conversation_id>/messages", methods=["GET"])
@requires_selected_api_key
@login_required
def get_paginated_messages(conversation_id):
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)  # Adjust the per_page as needed

    conversation = Conversation.query.get_or_404(conversation_id)
    if conversation.user_id != current_user.id:
        return jsonify({"error": "Unauthorized access"}), 403

    paginated_messages = (
        Message.query.filter_by(conversation_id=conversation_id)
        .order_by(Message.created_at.desc())
        .paginate(page=page, per_page=per_page)
    )

    messages = [
        {"id": message.id, "content": message.content, "created_at": message.created_at.isoformat()}
        for message in paginated_messages.items
    ]

    return jsonify(
        {"messages": messages, "has_next": paginated_messages.has_next, "next_page": paginated_messages.next_num}
    )


@chat_bp.route("/update-system-prompt/<string:conversation_id>", methods=["POST"])
@requires_selected_api_key
@login_required
def update_system_prompt(conversation_id):
    data = request.get_json()
    new_system_prompt = data.get("system_prompt")

    if new_system_prompt.strip() is None or not new_system_prompt.strip() or len(new_system_prompt.strip()) >= 2048:
        return (
            jsonify({"status": "error", "message": "System prompt must be provided. " "(Less than 1000 characters)."}),
            400,
        )

    conversation = Conversation.query.get_or_404(conversation_id)

    if conversation.user_id != current_user.id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    conversation.system_prompt = new_system_prompt.strip()
    try:
        db.session.commit()
        return jsonify({"status": "success", "message": "System prompt updated successfully."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)})


@chat_bp.route("/edit-message/<string:message_id>", methods=["POST"])
@requires_selected_api_key
@login_required
def edit_message(message_id):
    data = request.get_json()
    new_content = data.get("content")
    if new_content is None or not new_content.strip():
        return jsonify({"status": "error", "message": "Content must be provided and not just whitespace."}), 400

    message = Message.query.get_or_404(message_id)

    if message.conversation.user_id != current_user.id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    message.content = new_content.strip()
    try:
        db.session.commit()
        return jsonify({"status": "success", "message": "Message updated successfully."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)})


@chat_bp.route("/check-new-messages/<string:conversation_id>", methods=["GET"])
@requires_selected_api_key
@login_required
def check_new_messages(conversation_id):
    # Get the conversation from the database
    conversation = Conversation.query.get_or_404(conversation_id)

    # Get the last_checked_time from the conversation
    last_checked_time = conversation.last_checked_time

    # Query the database for new messages
    new_messages = Message.query.filter(
        Message.conversation_id == conversation_id, Message.created_at > last_checked_time
    ).all()

    # Convert the new messages to a list of dictionaries
    new_messages_dict = [
        {
            "id": message.id,
            "content": message.content,
            "className": "assistant-message" if message.direction == "incoming" else "user-message",
            "created_at": message.created_at.isoformat(),
        }
        for message in new_messages
    ]
    conversation.last_checked_time = datetime.utcnow()
    db.session.commit()

    return jsonify({"status": "success", "new_messages": new_messages_dict})


@chat_bp.route("/interrupt-stream/<string:conversation_id>", methods=["POST"])
@login_required
def interrupt_stream(conversation_id):
    conversation = Conversation.query.get_or_404(conversation_id)
    if conversation.user_id != current_user.id:
        abort(403)  # HTTP 403 Forbidden

    set_interruption_flag(conversation_id)

    return jsonify({"status": "success", "message": "Interruption signal received."})
