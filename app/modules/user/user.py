import os
from datetime import timedelta, datetime

from flask import Blueprint, render_template, redirect, url_for, request, jsonify, current_app
from flask_login import login_required, current_user
from markdown2 import markdown

from app import db
from app.models.image_models import GeneratedImage
from app.models.embedding_models import Document
from app.models.chat_models import ChatPreferences
from app.models.user_models import UserAPIKey, User, Role
from app.modules.chat.chat import model_to_dict
from app.utils.forms_util import (
    ChangeUsernameForm,
    UploadAPIKeyForm,
    DeleteAPIKeyForm,
    RetestAPIKeyForm,
    SelectAPIKeyForm,
    UserPreferencesForm,
    UpdateDocPreferencesForm,
)
from app.modules.auth.auth_util import (
    check_available_models,
    decrypt_api_key,
    hash_api_key,
    get_unique_nickname,
    create_and_save_api_key,
    test_api_key_models,
    api_key_exists,
    is_valid_api_key_format,
)

user_bp = Blueprint("user_bp", __name__, template_folder="templates", static_folder="static", url_prefix="/user")


@user_bp.route("/")
@login_required
def dashboard():
    user_api_keys = (
        UserAPIKey.query.filter_by(user_id=current_user.id, delete=False).filter(UserAPIKey.label != "Error").all()
    )
    selected_api_key_id = current_user.selected_api_key_id
    # Retrieve the user's img from the database ordered by 'id' descending
    user_images = (
        GeneratedImage.query.filter_by(user_id=current_user.id, delete=False)  # Add delete=False to the filter
        .order_by(GeneratedImage.created_at.desc())
        .limit(15)
        .all()
    )

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

    preferences = ChatPreferences.query.filter_by(user_id=current_user.id).first()
    if not preferences:
        preferences = ChatPreferences(user_id=current_user.id)
        db.session.add(preferences)
        db.session.commit()

    preferences_dict = model_to_dict(preferences)
    markdown_file_path = os.path.join(current_app.root_path, user_bp.static_folder, "user.md")
    user_role = Role.query.filter_by(id=current_user.role_id).first().name if current_user.role_id else None

    with open(markdown_file_path, "r") as file:
        markdown_content = file.read()
    docs_content = markdown(markdown_content)
    return render_template(
        "dashboard.html",
        user_api_keys=user_api_keys,
        selected_api_key_id=selected_api_key_id,
        user_images=user_images,
        current_user=current_user,
        documents=documents_data,
        preferences_dict=preferences_dict,
        user_preferences_form=UserPreferencesForm(data=preferences_dict),
        doc_preferences_form=UpdateDocPreferencesForm(data=preferences_dict),
        tooltip=docs_content,
        user_role=user_role,
        user_id=current_user.id,
    )


@user_bp.route("/change_username", methods=["POST"])
@login_required
def change_username():
    form = ChangeUsernameForm()
    if form.validate_on_submit():
        new_username = request.form.get("new_username").strip()

        if current_user.last_username_change and datetime.utcnow() - current_user.last_username_change < timedelta(
            days=7
        ):
            return jsonify({"status": "error", "message": "You can only change your username once every 7 days."}), 429

        if User.query.filter_by(username=new_username).first():
            return jsonify({"status": "error", "message": "This username is already taken."}), 400

        current_user.username = new_username
        current_user.last_username_change = datetime.utcnow()
        db.session.commit()
        return jsonify({"status": "success", "message": "Your username has been updated."}), 200


@user_bp.route("/upload_api_key", methods=["POST"])
@login_required
def upload_api_key():
    form = UploadAPIKeyForm()
    if form.validate_on_submit():
        data = request.get_json()
        api_key = data.get("api_key")
        nickname = data.get("nickname")

        if not is_valid_api_key_format(api_key):
            return jsonify({"status": "error", "message": "Invalid API key format."}), 400

        if api_key_exists(current_user.id, hash_api_key(api_key)):
            return jsonify({"status": "error", "message": "API key processing failed."}), 400

        try:
            available_models = check_available_models(api_key)
            label = test_api_key_models(api_key, available_models) if available_models else "Error"

            if label == "Skip":
                return jsonify({"status": "error", "message": "API key could not be verified at this time."}), 400
            elif label == "Error":
                nickname = get_unique_nickname(current_user.id, nickname)
                create_and_save_api_key(current_user.id, api_key, nickname, label)
                return jsonify({"status": "error", "message": f"{api_key} is not valid."}), 400

            nickname = get_unique_nickname(current_user.id, nickname)
            create_and_save_api_key(current_user.id, api_key, nickname, label)

            return (
                jsonify({"status": "success", "message": f"{api_key} added successfully with access to: {label}"}),
                200,
            )
        except Exception as e:
            db.session.rollback()
            return jsonify({"status": "error", "message": "Failed to verify API key."}), 400


@user_bp.route("/retest_api_key", methods=["POST"])
@login_required
def retest_api_key():
    form = RetestAPIKeyForm()
    if form.validate_on_submit():
        key_id = form.key_id.data
        user_api_key = UserAPIKey.query.filter_by(user_id=current_user.id, id=key_id, delete=False).first()

        if not user_api_key:
            return jsonify({"success": False, "message": "API key not found"}), 404

        api_key = decrypt_api_key(user_api_key.encrypted_api_key)
        nickname = user_api_key.nickname

        try:
            available_models = check_available_models(api_key)
            label = test_api_key_models(api_key, available_models) if available_models else "Error"

            if label == "Skip":
                return jsonify({"status": "error", "message": "API key could not be verified at this time."}), 400
            elif label == "Error":
                user_api_key.label = label
                db.session.commit()
                return jsonify({"status": "error", "message": "API key test failed, label set to Error"}), 400

            user_api_key.label = label
            db.session.commit()

            return jsonify({"status": "success", "message": f'API key "{nickname}" retested successfully'}), 200
        except Exception:
            db.session.rollback()
            return jsonify({"status": "error", "message": "Failed to retest API key"}), 400
    else:
        return jsonify({"status": "error", "message": "Invalid form submission."}), 400


@user_bp.route("/delete_api_key", methods=["POST"])
@login_required
def delete_api_key():
    form = DeleteAPIKeyForm()
    if form.validate_on_submit():
        key_id = form.key_id.data
        user_api_key = UserAPIKey.query.filter_by(user_id=current_user.id, id=key_id, delete=False).first()
        if user_api_key:
            user_api_key.delete = True  # Mark the API key as deleted
            current_user.selected_api_key_id = None
            db.session.commit()
            return (
                jsonify(
                    {
                        "status": "success",
                        "message": f'API key "{user_api_key.nickname}" marked for deletion successfully',
                    }
                ),
                200,
            )
        else:
            return jsonify({"status": "error", "message": "API key not found or already marked for deletion"}), 400
    return redirect(url_for("user_bp.dashboard"))


@user_bp.route("/select_api_key", methods=["POST"])
@login_required
def select_api_key():
    form = SelectAPIKeyForm()
    if form.validate_on_submit():
        key_id = request.form.get("key_id")
        user_api_key = UserAPIKey.query.filter_by(user_id=current_user.id, id=key_id, delete=False).first()

        if not user_api_key:
            return jsonify({"success": False, "message": "API key not found"}), 404

        api_key = decrypt_api_key(user_api_key.encrypted_api_key)
        try:
            available_models = check_available_models(api_key)
            is_valid_key = "gpt-3.5-turbo" in available_models or "gpt-4" in available_models

            if not is_valid_key:
                return jsonify({"success": False, "status": "error", "message": "API key is not valid."}), 400

            current_user.selected_api_key_id = user_api_key.id
            db.session.commit()
            return (
                jsonify({"success": True, "status": "success", "message": "API key " "selected successfully."}),
                200,
            )

        except Exception:
            db.session.rollback()
            return jsonify({"success": False, "status": "error", "message": "Failed to verify API key"}), 400
    else:
        return jsonify({"success": False, "message": "Invalid form submission."}), 400
