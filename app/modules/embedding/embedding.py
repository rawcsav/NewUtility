import os
from datetime import datetime

from flask import Blueprint, jsonify, render_template, request, session, current_app
from flask_login import login_required, current_user
from markdown2 import markdown
from werkzeug.utils import secure_filename

from app import db
from app.models.chat_models import ChatPreferences
from app.models.embedding_models import Document, DocumentChunk
from app.modules.auth.auth_util import initialize_openai_client
from app.modules.embedding.embedding_util import (
    split_text,
    extract_text_from_file,
    remove_temp,
    get_embedding_batch,
    store_embeddings,
    save_temp,
)
from app.utils.forms_util import DocumentUploadForm, EditDocumentForm, DeleteDocumentForm, UpdateDocPreferencesForm
from app.utils.usage_util import embedding_cost
from app.utils.vector_cache import VectorCache

# Initialize the blueprint
embedding_bp = Blueprint(
    "embedding_bp", __name__, template_folder="templates", static_folder="static", url_prefix="/embedding"
)


@embedding_bp.route("/", methods=["GET"])
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

    return render_template("embedding.html", documents=documents_data, tooltip=docs_content)


@embedding_bp.route("/upload", methods=["POST"])
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

    uploaded_files_info = []
    for i, file in enumerate(files):
        title = titles[i] if i < len(titles) else secure_filename(file.filename)
        author = authors[i] if i < len(authors) else ""
        chunk_size = int(chunk_sizes[i]) if i < len(chunk_sizes) else 512

        temp_path = save_temp(file)
        uploaded_files_info.append({"temp_path": temp_path, "title": title, "author": author, "chunk_size": chunk_size})

    session["uploaded_files_info"] = uploaded_files_info

    return (
        jsonify({"status": "success", "message": "Files uploaded successfully. Please proceed to processing."}),
        200,
    )


@embedding_bp.route("/process/<int:doc_index>", methods=["POST"])
@login_required
def process_individual_document(doc_index):
    # Retrieve uploaded files info from the session
    uploaded_files_info = session.get("uploaded_files_info", [])

    # Validate document index
    if doc_index < 0 or doc_index >= len(uploaded_files_info):
        return jsonify({"error": "Invalid document index"}), 400

    file_info = uploaded_files_info[doc_index]

    try:
        temp_path = file_info["temp_path"]
        title = file_info["title"]
        author = file_info["author"]
        chunk_size = file_info["chunk_size"]

        file_info["status"] = "Processing"
        session.modified = True

        # Processing steps for the individual document
        text_pages = extract_text_from_file(temp_path)
        chunks, chunk_pages, total_tokens, chunk_token_counts = split_text(text_pages, chunk_size)

        new_document = Document(
            user_id=current_user.id, title=title, author=author, total_tokens=total_tokens, created_at=datetime.utcnow()
        )
        db.session.add(new_document)
        db.session.flush()

        for i, (chunk_content, pages) in enumerate(zip(chunks, chunk_pages)):
            pages_str = ",".join(map(str, pages))
            chunk = DocumentChunk(
                document_id=new_document.id,
                chunk_index=i,
                content=chunk_content,
                tokens=chunk_token_counts[i],
                pages=pages_str,
            )
            db.session.add(chunk)

        # Assuming the existence of the following functions
        client, error = initialize_openai_client(current_user.id)
        if error:
            return jsonify({"status": "error", "message": error})

        embeddings = get_embedding_batch(chunks, client)

        embedding_cost(total_tokens)

        store_embeddings(new_document.id, embeddings)
        db.session.commit()

        file_info["status"] = "Complete"
        session.modified = True
        return jsonify({"status": "success", "message": "Document processed successfully."}), 200

    except Exception as e:
        db.session.rollback()
        file_info["status"] = "Error"
        session.modified = True
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        remove_temp(file_info["temp_path"])


@embedding_bp.route("/status", methods=["GET"])
@login_required
def get_processing_status():
    uploaded_files_info = session.get("uploaded_files_info", [])
    if not uploaded_files_info:
        return jsonify({"error": "No documents found"}), 404

    # Extracting only relevant data for the frontend
    status_info = [{"title": f["title"], "status": f["status"]} for f in uploaded_files_info]
    return jsonify(status_info)


@embedding_bp.route("/delete/<string:document_id>", methods=["POST"])
@login_required
def delete_document(document_id):
    form = DeleteDocumentForm()
    document = Document.query.get_or_404(document_id)
    if document.user_id != current_user.id or not form.validate_on_submit():
        return jsonify({"error": "Unauthorized or invalid form submission"}), 403

    try:
        document.delete = True
        db.session.commit()
        return (
            jsonify(
                {"status": "success", "message": "Document deleted successfully." "\nPlease refresh to see changes"}
            ),
            200,
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500


@embedding_bp.route("/update", methods=["POST"])
@login_required
def update_document():
    form = EditDocumentForm()
    if not form.validate_on_submit():
        return jsonify({"error": "Invalid form submission"}), 400

    document_id = form.document_id.data
    title = form.title.data
    author = form.author.data

    document = Document.query.get_or_404(document_id)
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
@login_required
def update_knowledge_query_mode():
    data = request.get_json()
    knowledge_query_mode = data["knowledge_query_mode"]

    # Assuming you have a ChatPreferences model with a knowledge_query_mode field
    chat_preferences = ChatPreferences.query.filter_by(user_id=current_user.id).first()
    chat_preferences.knowledge_query_mode = knowledge_query_mode
    db.session.commit()

    return jsonify({"status": "success"})


@embedding_bp.route("/update-knowledge-context-tokens", methods=["POST"])
@login_required
def update_knowledge_context_tokens():
    data = request.get_json()
    knowledge_context_tokens = float(data["knowledge_context_tokens"])
    chat_preferences = ChatPreferences.query.filter_by(user_id=current_user.id).first()
    chat_preferences.knowledge_context_tokens = knowledge_context_tokens
    db.session.commit()

    return jsonify({"status": "success"})


@embedding_bp.route("/update-doc-preferences", methods=["POST"])
@login_required
def update_docs_preferences():
    form = UpdateDocPreferencesForm()
    if form.validate_on_submit():
        form_data = request.form
        chat_preferences = ChatPreferences.query.filter_by(user_id=current_user.id).first()
        chat_preferences.knowledge_query_mode = "knowledge_query_mode" in form_data
        if chat_preferences.knowledge_query_mode:
            VectorCache.load_user_vectors(current_user.id)
        chat_preferences.knowledge_context_tokens = int(form_data.get("knowledge_context_tokens", 0))

        Document.query.filter_by(user_id=current_user.id).update({"selected": False})

        for key in form_data.keys():
            if key.startswith("document_selection_"):
                doc_id = key.split("_")[-1]
                document = Document.query.get(doc_id)
                if document and document.user_id == current_user.id:
                    document.selected = True
        try:
            db.session.commit()
            return jsonify({"status": "success", "message": "Preferences updated successfully."})
        except Exception as e:
            db.session.rollback()
            return jsonify({"status": "error", "message": str(e)})
