import os
from flask import Blueprint, jsonify, render_template, request, session, current_app
from flask_login import login_required, current_user
from markdown2 import markdown
from werkzeug.utils import secure_filename

from app.modules.auth.auth_util import requires_selected_api_key
from app.tasks.embedding_task import process_embedding_task
from app import db
from app.models.chat_models import ChatPreferences
from app.models.embedding_models import Document
from app.models.task_models import EmbeddingTask, Task
from app.modules.embedding.embedding_util import save_temp
from app.utils.forms_util import DocumentUploadForm, EditDocumentForm, DeleteDocumentForm, UpdateDocPreferencesForm
from app.utils.vector_cache import VectorCache

# Initialize the blueprint
embedding_bp = Blueprint(
    "embedding_bp", __name__, template_folder="templates", static_folder="static", url_prefix="/embedding"
)


@embedding_bp.route("/", methods=["GET"])
@requires_selected_api_key
@login_required
def embeddings_center():
    markdown_file_path = os.path.join(current_app.root_path, embedding_bp.static_folder, "embedding.md")

    with open(markdown_file_path, "r") as file:
        markdown_content = file.read()
    docs_content = markdown(markdown_content)
    user_documents = Document.query.filter_by(user_id=current_user.id, delete=False).all()
    # Prepare document data for the template
    documents_data = [
        {
            "id": doc.id,
            "title": doc.title,
            "author": doc.author,
            "total_tokens": doc.total_tokens,
            "chunk_count": len(doc.chunks),
        }
        for doc in user_documents
    ]

    return render_template("embedding.html", documents=documents_data)


@embedding_bp.route("/upload", methods=["POST"])
@requires_selected_api_key
@login_required
def upload_document():
    form = DocumentUploadForm()
    if not form.validate_on_submit():
        return jsonify({"error": "Invalid form submission"}), 400

    files = request.files.getlist("file")
    if not files:
        return jsonify({"error": "No files provided"}), 400

    # Get titles, authors, and chunk_sizes for all documents
    titles = request.form.getlist("title")
    authors = request.form.getlist("author")
    chunk_sizes = request.form.getlist("chunk_size")
    advanced_preprocessings = request.form.getlist("advanced_preprocessing")  # Capture advanced preprocessing options

    tasks_info = []  # To keep track of created tasks and associated file info

    for i, file in enumerate(files):
        title = titles[i] if i < len(titles) else secure_filename(file.filename)
        author = authors[i] if i < len(authors) else ""
        chunk_size = int(chunk_sizes[i]) if i < len(chunk_sizes) else 512
        advanced_preprocessing = (
            advanced_preprocessings[i] == "true" if i < len(advanced_preprocessings) else False
        )  # Convert to boolean

        temp_path = save_temp(file)

        new_task = Task(type="Embedding", status="pending", user_id=current_user.id)
        db.session.add(new_task)
        db.session.flush()

        new_embedding_task = EmbeddingTask(
            task_id=new_task.id,
            title=title,
            author=author,
            chunk_size=chunk_size,
            temp_path=temp_path,
            advanced_preprocessing=advanced_preprocessing,
        )
        db.session.add(new_embedding_task)

        tasks_info.append(
            {"task_id": new_task.id, "title": title, "author": author, "chunk_size": chunk_size, "temp_path": temp_path}
        )

    db.session.commit()
    for task_info in tasks_info:
        process_embedding_task.apply_async(kwargs={"task_id": task_info["task_id"]})

    return jsonify({"status": "success", "tasks": [{"task_id": task["task_id"]} for task in tasks_info]}), 200


@embedding_bp.route("/status", methods=["GET"])
@requires_selected_api_key
@login_required
def get_processing_status():
    uploaded_files_info = session.get("uploaded_files_info", [])
    if not uploaded_files_info:
        return jsonify({"error": "No documents found"}), 404

    # Extracting only relevant data for the frontend
    status_info = [{"title": f["title"], "status": f["status"]} for f in uploaded_files_info]
    return jsonify(status_info)


@embedding_bp.route("/delete/<string:document_id>", methods=["POST"])
@requires_selected_api_key
@login_required
def delete_document(document_id):
    form = DeleteDocumentForm()
    document = Document.query.filter_by(user_id=current_user.id, id=document_id, delete=False).first()
    if document.user_id != current_user.id or not form.validate_on_submit():
        return jsonify({"error": "Unauthorized or invalid form submission"}), 403
    try:
        document.delete = True
        db.session.commit()
        return (jsonify({"status": "success", "message": "Document deleted successfully."}), 200)
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500


@embedding_bp.route("/delete_all", methods=["POST"])
@requires_selected_api_key
@login_required
def delete_all_documents():
    try:
        documents = Document.query.filter_by(user_id=current_user.id, delete=False).all()

        if not documents:
            return jsonify({"status": "success", "message": "No documents to delete."}), 200

        for document in documents:
            document.delete = True
        db.session.commit()

        return (
            jsonify(
                {"status": "success", "message": "All documents deleted successfully.\nPlease refresh to see changes"}
            ),
            200,
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500


@embedding_bp.route("/update", methods=["POST"])
@requires_selected_api_key
@login_required
def update_document():
    form = EditDocumentForm()
    if not form.validate_on_submit():
        return jsonify({"error": "Invalid form submission"}), 400

    document_id = form.document_id.data
    title = form.title.data
    author = form.author.data

    document = Document.query.filter_by(user_id=current_user.id, id=document_id, delete=False).first()
    if document.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        if title:
            document.title = title
        if author:
            document.author = author
        db.session.commit()
        return (
            jsonify(
                {"status": "success", "message": "Document updated successfully." "\nPlease refresh to see changes"}
            ),
            200,
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500


@embedding_bp.route("/update-document-selection", methods=["POST"])
@requires_selected_api_key
@login_required
def update_document_selection():
    data = request.get_json()
    document_id = data["document_id"]
    selected = data["selected"]

    # Assuming you have a Document model with a selected field
    document = Document.query.get(document_id)
    if document.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    document.selected = selected
    db.session.commit()

    return jsonify({"status": "success"})


@embedding_bp.route("/update-knowledge-query-mode", methods=["POST"])
@requires_selected_api_key
@login_required
def update_knowledge_query_mode():
    data = request.get_json()
    knowledge_query_mode = data["knowledge_query_mode"]

    # Assuming you have a ChatPreferences model with a knowledge_query_mode field
    chat_preferences = ChatPreferences.query.filter_by(user_id=current_user.id).first()
    chat_preferences.knowledge_query_mode = knowledge_query_mode
    db.session.commit()

    return jsonify({"status": "success"})


@embedding_bp.route("/update-top-k", methods=["POST"])
@requires_selected_api_key
@login_required
def update_top_k():
    data = request.get_json()
    top_k = float(data["top_k"])
    chat_preferences = ChatPreferences.query.filter_by(user_id=current_user.id).first()
    chat_preferences.top_k = top_k
    db.session.commit()

    return jsonify({"status": "success"})


@embedding_bp.route("/update-doc-preferences", methods=["POST"])
@requires_selected_api_key
@login_required
def update_docs_preferences():
    form = UpdateDocPreferencesForm()
    if form.validate_on_submit():
        form_data = request.form
        chat_preferences = ChatPreferences.query.filter_by(user_id=current_user.id).first()

        # Update knowledge query mode
        chat_preferences.knowledge_query_mode = "knowledge_query_mode" in form_data
        if chat_preferences.knowledge_query_mode:
            VectorCache.load_user_vectors(current_user.id)

        chat_preferences.top_k = int(form_data.get("top_k", 0))

        if "threshold" in form_data:
            try:
                threshold = float(form_data.get("threshold"))
                if 0.0 <= threshold <= 1.0:
                    chat_preferences.threshold = threshold
                else:
                    return jsonify({"status": "error", "message": "Threshold must be between 0.0 and 1.0."})
            except ValueError:
                return jsonify({"status": "error", "message": "Invalid threshold value."})

        if "system_prompt" in form_data:
            chat_preferences.cwd_system_prompt = form_data.get("system_prompt")

        if "temperature" in form_data:
            try:
                temperature = float(form_data.get("temperature"))
                if 0.0 <= temperature <= 2.0:
                    chat_preferences.temperature = temperature
                else:
                    return jsonify({"status": "error", "message": "Temperature must be between 0.0 and 1.0."})
            except ValueError:
                return jsonify({"status": "error", "message": "Invalid temperature value."})

        if "top_p" in form_data:
            try:
                top_p = float(form_data.get("top_p"))
                if 0.0 <= top_p <= 1.0:
                    chat_preferences.top_p = top_p
                else:
                    return jsonify({"status": "error", "message": "Top P must be between 0.0 and 1.0."})
            except ValueError:
                return jsonify({"status": "error", "message": "Invalid top P value."})

        Document.query.filter_by(user_id=current_user.id).update({"selected": False})
        for key in form_data.keys():
            if key.startswith("document_selection_"):
                doc_id = key.split("_")[-1]
                document = Document.query.get(doc_id)
                if document and document.user_id == current_user.id:
                    document.selected = True

        if "reset" in form_data:
            # Reset preferences to default values
            chat_preferences.knowledge_query_mode = False
            chat_preferences.top_k = 10
            chat_preferences.threshold = 0.5
            chat_preferences.cwd_system_prompt = "You are a helpful academic literary assistant. Provide in -depth guidance, suggestions, code snippets, and explanations as needed to help the user. Leverage your expertise and intuition to offer innovative and effective solutions.Be informative, clear, and concise in your responses, and focus on providing accurate and reliable information. Use the provided text excerpts directly to aid in your responses."
            chat_preferences.temperature = 1.0
            chat_preferences.top_p = 1.0
        try:
            db.session.commit()
            return jsonify({"status": "success", "message": "Preferences updated successfully."})
        except Exception as e:
            db.session.rollback()
            return jsonify({"status": "error", "message": str(e)})

    return jsonify({"status": "error", "message": "Invalid form submission."})
