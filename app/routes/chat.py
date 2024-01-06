from datetime import datetime

from flask import jsonify, Response, abort, session
from flask import render_template, flash, request, Blueprint
from flask_login import login_required, current_user

from app import db
from app.database import ChatPreferences, Conversation, Message, MessageImages, Document
from app.util.chat_util import (
    get_user_preferences,
    user_history,
    handle_stream,
    handle_nonstream,
    allowed_file,
    save_image,
    get_image_url,
    retry_delete_messages,
    delete_local_image_file,
    set_interruption_flag,
)
from app.util.embeddings_util import append_knowledge_context
from app.util.forms_util import (
    ChatCompletionForm,
    UserPreferencesForm,
    NewConversationForm,
    UpdateDocPreferencesForm,
)
from app.util.session_util import initialize_openai_client
from sqlalchemy.inspection import inspect

bp = Blueprint("chat", __name__, url_prefix="/chat")


def model_to_dict(model):
    return {c.key: getattr(model, c.key) for c in inspect(model).mapper.column_attrs}


@bp.route("/", methods=["GET"])
@login_required
def chat_index():
    # Create form instances
    new_conversation_form = NewConversationForm()
    chat_completion_form = ChatCompletionForm()

    conversation_history = Conversation.query.filter_by(user_id=current_user.id).all()

    if not conversation_history:
        new_conversation = Conversation(
            user_id=current_user.id,
            system_prompt=new_conversation_form.system_prompt.data,
        )
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

    if preferences.model == "gpt-4-vision-preview":
        images_without_message_id = MessageImages.query.filter(
            MessageImages.user_id == current_user.id, MessageImages.message_id.is_(None)
        ).all()

        # Convert the images to a list of URLs
        image_urls = [image.image_url for image in images_without_message_id]
    else:
        image_urls = []

    user_documents = Document.query.filter_by(
        user_id=current_user.id, delete=False
    ).all()
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
    # Pass the image URLs to the template
    return render_template(
        "chat_page.html",
        new_conversation_form=new_conversation_form,
        user_preferences_form=user_preferences_form,
        chat_completion_form=chat_completion_form,
        conversation_history=conversation_history_data,
        image_urls=image_urls,
        documents=documents_data,
        preferences_dict=preferences_dict,
        doc_preferences_form=UpdateDocPreferencesForm(data=preferences_dict),
    )


@bp.route("/new-conversation", methods=["POST"])
@login_required
def new_conversation():
    form = NewConversationForm()
    if form.validate_on_submit():
        user_id = current_user.id
        # Fetch all conversations for the user that start with "Convo #"
        existing_conversations = Conversation.query.filter(
            Conversation.user_id == user_id, Conversation.title.like("Convo #%")
        ).all()

        convo_numbers = [
            int(c.title.split("#")[-1])
            for c in existing_conversations
            if c.title.split("#")[-1].isdigit()
        ]
        max_number = max(convo_numbers) if convo_numbers else 0

        new_title = f"Convo #{max_number + 1}"

        # Create new conversation with the generated title
        new_conversation = Conversation(
            user_id=user_id, title=new_title, system_prompt=form.system_prompt.data
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


@bp.route("/delete-conversation/<string:conversation_id>", methods=["POST"])
@login_required
def delete_conversation(conversation_id):
    conversation_to_delete = Conversation.query.get_or_404(conversation_id)
    if conversation_to_delete.user_id != current_user.id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    # Check if this is the user's last conversation
    conversation_count = Conversation.query.filter_by(user_id=current_user.id).count()
    if conversation_count <= 1:
        return (
            jsonify({"status": "error", "message": "Cannot have 0 conversations."}),
            403,
        )

    db.session.delete(conversation_to_delete)
    try:
        db.session.commit()
        return jsonify(
            {"status": "success", "message": "Conversation deleted successfully."}
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)})


@bp.route("/update-preferences", methods=["POST"])
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
        preferences.stream = form.stream.data

        if (
            old_model == "gpt-4-vision-preview"
            and form.model.data != "gpt-4-vision-preview"
        ):
            MessageImages.query.filter_by(user_id=current_user.id).delete()

            message_ids_with_images = MessageImages.query.with_entities(
                MessageImages.message_id
            ).filter_by(user_id=current_user.id)
            Message.query.filter(Message.id.in_(message_ids_with_images)).update(
                {Message.is_vision: False}, synchronize_session="fetch"
            )

        try:
            db.session.commit()
            return jsonify(
                {"status": "success", "message": "Preferences updated successfully."}
            )
        except Exception as e:
            db.session.rollback()
            return jsonify({"status": "error", "message": str(e)})
    else:
        return jsonify({"status": "error", "errors": form.errors})


@bp.route("/completion", methods=["POST"])
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
    stream_preference = preferences.get("stream", True)
    raw_prompt = form.prompt.data
    try:
        # Call append_knowledge_context and handle different return values
        result = append_knowledge_context(raw_prompt, user_id, client)

        # If the result is a tuple, unpack it accordingly
        if isinstance(result, tuple):
            if len(result) == 2:
                prompt, chunk_associations = result
            elif len(result) == 1:
                # If only one value is returned, it wasn't a knowledge query
                (prompt,) = result
                chunk_associations = None
            else:
                # This block will handle more than two values returned
                prompt = result[0] if len(result) > 0 else None
                chunk_associations = None
        else:
            # If the result is not a tuple, assume it's just the prompt
            prompt = result
            chunk_associations = None

    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    session["interruption"] = None

    if preferences["model"] == "gpt-4-vision-preview":
        images = MessageImages.query.filter(
            MessageImages.user_id == current_user.id, MessageImages.message_id.is_(None)
        ).all()
        image_urls = [image.image_url for image in images]
    else:
        image_urls = []
    try:
        if stream_preference:
            response, _ = handle_stream(
                raw_prompt,
                prompt,
                client,
                user_id,
                conversation_id,
                image_urls,
                chunk_associations=chunk_associations,
            )
            return Response(
                response, content_type="text/plain", headers={"X-Accel-Buffering": "no"}
            )
        else:
            full_response = handle_nonstream(
                raw_prompt,
                prompt,
                client,
                user_id,
                conversation_id,
                image_urls,
                chunk_associations=chunk_associations,
            )
            if full_response:
                return jsonify({"status": "success", "message": full_response.strip()})
            else:
                return jsonify(
                    {"status": "warning", "message": "No response from the AI."}
                )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@bp.route("/conversation/<string:conversation_id>", methods=["GET"])
@login_required
def get_conversation_messages(conversation_id):
    conversation, conversation_history = user_history(current_user.id, conversation_id)
    if conversation:
        messages = [
            {
                "content": message["content"],
                "className": message["role"] + "-message",
                "messageId": message["id"],
                "images": message.get("images", []),
            }
            for message in conversation_history
        ]
        conversation.last_checked_time = datetime.utcnow()
        db.session.commit()
        return jsonify({"messages": messages})
    else:
        return jsonify({"error": "Conversation not found"}), 404


@bp.route("/update-conversation-title/<string:conversation_id>", methods=["POST"])
@login_required
def update_conversation_title(conversation_id):
    data = request.get_json()
    new_title = data.get("title")

    # Validate new_title: not None, not just whitespace, and 25 characters or fewer
    if new_title is None or not new_title.strip() or len(new_title.strip()) > 25:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Title must be provided (25 characters or fewer).",
                }
            ),
            400,
        )

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


@bp.route("/conversation/<string:conversation_id>/messages", methods=["GET"])
@login_required
def get_paginated_messages(conversation_id):
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get(
        "per_page", 10, type=int
    )  # Adjust the per_page as needed

    conversation = Conversation.query.get_or_404(conversation_id)
    if conversation.user_id != current_user.id:
        return jsonify({"error": "Unauthorized access"}), 403

    paginated_messages = (
        Message.query.filter_by(conversation_id=conversation_id)
        .order_by(Message.created_at.desc())
        .paginate(page=page, per_page=per_page)
    )

    messages = [
        {
            "id": message.id,
            "content": message.content,
            "created_at": message.created_at.isoformat(),
        }
        for message in paginated_messages.items
    ]

    return jsonify(
        {
            "messages": messages,
            "has_next": paginated_messages.has_next,
            "next_page": paginated_messages.next_num,
        }
    )


@bp.route("/update-system-prompt/<string:conversation_id>", methods=["POST"])
@login_required
def update_system_prompt(conversation_id):
    data = request.get_json()
    new_system_prompt = data.get("system_prompt")

    if (
        new_system_prompt.strip() is None
        or not new_system_prompt.strip()
        or len(new_system_prompt.strip()) >= 1000
    ):
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "System prompt must be provided. "
                    "(Less than 1000 characters).",
                }
            ),
            400,
        )

    conversation = Conversation.query.get_or_404(conversation_id)

    if conversation.user_id != current_user.id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    conversation.system_prompt = new_system_prompt.strip()
    try:
        db.session.commit()
        return jsonify(
            {"status": "success", "message": "System prompt updated successfully."}
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)})


@bp.route("/edit-message/<string:message_id>", methods=["POST"])
@login_required
def edit_message(message_id):
    data = request.get_json()
    new_content = data.get("content")

    # Validate new_content: not None and not just whitespace
    if new_content is None or not new_content.strip():
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Content must be provided and not just whitespace.",
                }
            ),
            400,
        )

    message = Message.query.get_or_404(message_id)

    # Check if the current user is authorized to edit the message
    if message.conversation.user_id != current_user.id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    # Update the message content with the validated and stripped content
    message.content = new_content.strip()
    try:
        db.session.commit()
        return jsonify(
            {"status": "success", "message": "Message updated successfully."}
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)})


@bp.route("/check-new-messages/<string:conversation_id>", methods=["GET"])
@login_required
def check_new_messages(conversation_id):
    # Get the conversation from the database
    conversation = Conversation.query.get_or_404(conversation_id)

    # Get the last_checked_time from the conversation
    last_checked_time = conversation.last_checked_time

    # Query the database for new messages
    new_messages = Message.query.filter(
        Message.conversation_id == conversation_id,
        Message.created_at > last_checked_time,
    ).all()

    # Convert the new messages to a list of dictionaries
    new_messages_dict = [
        {
            "id": message.id,
            "content": message.content,
            "className": "assistant-message"
            if message.direction == "incoming"
            else "user-message",
            "created_at": message.created_at.isoformat(),
        }
        for message in new_messages
    ]

    return jsonify({"status": "success", "new_messages": new_messages_dict})


@bp.route("/retry-message/<string:message_id>", methods=["POST"])
@login_required
def retry_message(message_id):
    message = Message.query.get_or_404(message_id)
    conversation_id = message.conversation_id
    message_id = message.id

    if message.conversation.user_id != current_user.id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    user_id = current_user.id
    client, error = initialize_openai_client(user_id)
    if error:
        return jsonify({"status": "error", "message": error})

    preferences = get_user_preferences(user_id)
    stream_preference = preferences.get("stream", True)
    prompt = message.content
    if message.is_vision:
        images = MessageImages.query.filter(
            MessageImages.user_id == current_user.id,
            MessageImages.message_id == message.id,
        ).all()
        image_urls = [image.image_url for image in images]
    else:
        image_urls = []
    try:
        retry_delete_messages(conversation_id, message_id)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    try:
        if stream_preference:
            response, full_response = handle_stream(
                prompt, client, user_id, conversation_id, images=image_urls, retry=True
            )
            return Response(
                response, content_type="text/plain", headers={"X-Accel-Buffering": "no"}
            )
        else:
            full_response = handle_nonstream(
                prompt, client, user_id, conversation_id, images=image_urls, retry=True
            )
        if full_response:
            return jsonify({"status": "success", "message": full_response.strip()})
        else:
            return jsonify({"status": "warning", "message": "No response from the AI."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@bp.route("/interrupt-stream/<string:conversation_id>", methods=["POST"])
@login_required
def interrupt_stream(conversation_id):
    conversation = Conversation.query.get_or_404(conversation_id)
    if conversation.user_id != current_user.id:
        abort(403)  # HTTP 403 Forbidden

    set_interruption_flag(conversation_id)
    print(f"Interruption flag set in session for conversation {conversation_id}")

    return jsonify({"status": "success", "message": "Interruption signal received."})


@bp.route("/upload-chat-image", methods=["POST"])
def upload_image():
    file = request.files.get("file")
    conversation_id = request.form.get("conversation_id")
    print(f"Conversation ID: {conversation_id}")
    if file and allowed_file(file.filename) and conversation_id:
        try:
            image_uuid, webp_file_name = save_image(file.stream)
            webp_url = get_image_url(webp_file_name)

            new_image_entry = MessageImages(
                image_url=webp_url,
                uuid=image_uuid,
                user_id=current_user.id,
                conversation_id=conversation_id,
            )
            db.session.add(new_image_entry)
            db.session.commit()

            return (
                jsonify(
                    {
                        "status": "success",
                        "image_uuid": image_uuid,
                        "image_url": webp_url,
                        "conversation_id": conversation_id,
                    }
                ),
                200,
            )

        except Exception as e:
            db.session.rollback()
            return (
                jsonify({"status": "error", "message": f"Error processing image: {e}"}),
                500,
            )
    else:
        return jsonify({"status": "error", "message": "Invalid file upload"}), 400


@bp.route("/delete-image/<string:image_uuid>", methods=["POST"])
@login_required
def delete_image(image_uuid):
    image_record = MessageImages.query.filter_by(uuid=image_uuid).first()

    if image_record.user_id != current_user.id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403
    delete_local_image_file(image_uuid)
    db.session.delete(image_record)
    db.session.commit()

    return jsonify({"status": "success", "message": "Image deleted successfully"})
