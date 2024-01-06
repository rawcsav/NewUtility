from datetime import datetime
from flask import Blueprint, jsonify, render_template, request, session
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from openai import OpenAI
from app import db
from app.database import Document, DocumentChunk, UserAPIKey, ChatPreferences

from app.util.embeddings_util import (
    split_text,
    extract_text_from_file,
    remove_temp_file,
    get_embedding_batch,
    store_embeddings,
    save_temp_file,
    delete_all_documents,
)
from app.util.forms_util import (
    DocumentUploadForm,
    EditDocumentForm,
    DeleteDocumentForm,
    UpdateDocPreferencesForm,
)
from app.util.session_util import initialize_openai_client
from app.util.usage_util import embedding_cost, update_usage_and_costs

# Initialize the blueprint
bp = Blueprint("embeddings", __name__, url_prefix="/embeddings")


@bp.route("/embeddings", methods=["GET"])
@login_required
def embeddings_center():
    # Query the database for the current user's documents
    user_documents = Document.query.filter_by(
        user_id=current_user.id, delete=False
    ).all()
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

    return render_template("embeddings.html", documents=documents_data)


@bp.route("/upload", methods=["POST"])
@login_required
def upload_document():
    form = DocumentUploadForm()
    if not form.validate_on_submit():
        return jsonify({"error": "Invalid form submission"}), 400

    files = request.files.getlist("file")
    if not files:
        return jsonify({"error": "No files provided"}), 400

    titles = request.form.get("title", "").split(",") if "title" in request.form else []
    authors = (
        request.form.get("author", "").split(",") if "author" in request.form else []
    )

    uploaded_files_info = []

    for i, file in enumerate(files):
        title = (
            titles[i]
            if i < len(titles) and titles[i].strip()
            else secure_filename(file.filename)
        )
        author = authors[i].strip() if i < len(authors) and authors[i].strip() else None
        temp_path = save_temp_file(file)
        uploaded_files_info.append(
            {
                "temp_path": temp_path,
                "title": title,
                "author": author,
                "chunk_size": form.chunk_size.data or 512,
            }
        )

    session["uploaded_files_info"] = uploaded_files_info

    return (
        jsonify(
            {
                "status": "success",
                "message": "Files uploaded successfully. Please proceed to processing.",
            }
        ),
        200,
    )


@bp.route("/process", methods=["POST"])
@login_required
def process_document():
    # Retrieve uploaded files info from the session
    uploaded_files_info = session.get("uploaded_files_info", [])
    if not uploaded_files_info:
        return jsonify({"error": "No uploaded files to process"}), 400

    try:
        for file_info in uploaded_files_info:
            temp_path = file_info["temp_path"]
            title = file_info["title"]
            author = file_info["author"]
            chunk_size = file_info["chunk_size"]
            file_info['status'] = 'splitting'
            session.modified = True
            text_pages = extract_text_from_file(temp_path)
            chunks, chunk_pages, total_tokens, chunk_token_counts = split_text(
                text_pages, chunk_size
            )

            new_document = Document(
                user_id=current_user.id,
                title=title,
                author=author,
                total_tokens=total_tokens,
                created_at=datetime.utcnow(),
            )
            db.session.add(new_document)
            db.session.flush()  # Flush the session to get the new ID

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

            client, error = initialize_openai_client(current_user.id)
            if error:
                return jsonify({"status": "error", "message": error})
            file_info['status'] = 'embedding'
            session.modified = True
            embeddings = get_embedding_batch(chunks, client)

            cost = embedding_cost(total_tokens)
            update_usage_and_costs(
                user_id=current_user.id,
                api_key_id=current_user.selected_api_key_id,
                usage_type="embedding",
                cost=cost,
            )

            store_embeddings(new_document.id, embeddings)
            db.session.commit()
            file_info['status'] = 'complete'
            session.modified = True
        session.pop("uploaded_files_info", None)

        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Documents processed and embedded successfully.",
                }
            ),
            200,
        )

    except Exception as e:
        session.pop("uploaded_files_info", None)
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        for file_info in uploaded_files_info:
            remove_temp_file(file_info["temp_path"])

@bp.route("/status", methods=["GET"])
@login_required
def get_processing_status():
    uploaded_files_info = session.get("uploaded_files_info", [])
    if not uploaded_files_info:
        return jsonify({"error": "No documents found"}), 404

    # Extracting only relevant data for the frontend
    status_info = [{"title": f["title"], "status": f["status"]} for f in uploaded_files_info]
    return jsonify(status_info)

@bp.route("/delete/<string:document_id>", methods=["POST"])
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
                {
                    "status": "success",
                    "message": "Document deleted successfully."
                    "\nPlease refresh to see changes",
                }
            ),
            200,
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/update", methods=["POST"])
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
                {
                    "status": "success",
                    "message": "Document updated successfully."
                    "\nPlease refresh to see changes",
                }
            ),
            200,
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/update-document-selection", methods=["POST"])
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


@bp.route("/update-knowledge-query-mode", methods=["POST"])
@login_required
def update_knowledge_query_mode():
    data = request.get_json()
    knowledge_query_mode = data["knowledge_query_mode"]

    # Assuming you have a ChatPreferences model with a knowledge_query_mode field
    chat_preferences = ChatPreferences.query.filter_by(user_id=current_user.id).first()
    chat_preferences.knowledge_query_mode = knowledge_query_mode
    db.session.commit()

    return jsonify({"status": "success"})


@bp.route("/update-knowledge-context-tokens", methods=["POST"])
@login_required
def update_knowledge_context_tokens():
    data = request.get_json()
    knowledge_context_tokens = float(data["knowledge_context_tokens"])
    chat_preferences = ChatPreferences.query.filter_by(user_id=current_user.id).first()
    chat_preferences.knowledge_context_tokens = knowledge_context_tokens
    db.session.commit()

    return jsonify({"status": "success"})


@bp.route("/update-doc-preferences", methods=["POST"])
@login_required
def update_docs_preferences():
    form = UpdateDocPreferencesForm()
    if form.validate_on_submit():
        form_data = request.form
        chat_preferences = ChatPreferences.query.filter_by(
            user_id=current_user.id
        ).first()
        chat_preferences.knowledge_query_mode = "knowledge_query_mode" in form_data
        chat_preferences.knowledge_context_tokens = int(
            form_data.get("knowledge_context_tokens", 0)
        )

        Document.query.filter_by(user_id=current_user.id).update({"selected": False})

        for key in form_data.keys():
            if key.startswith("document_selection_"):
                doc_id = key.split("_")[-1]
                document = Document.query.get(doc_id)
                if document and document.user_id == current_user.id:
                    document.selected = True

        # Commit the changes to the database
        try:
            db.session.commit()
            return jsonify(
                {"status": "success", "message": "Preferences updated successfully."}
            )
        except Exception as e:
            db.session.rollback()
            return jsonify({"status": "error", "message": str(e)})
