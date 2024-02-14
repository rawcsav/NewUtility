import threading
from flask import Blueprint, render_template, request, jsonify, session
from flask_login import current_user

from app import db
from app.models.embedding_models import Document
from app.modules.auth.auth_util import initialize_openai_client
import os
from flask import request, stream_with_context, Blueprint, current_app

from app.modules.cwd.cwd_util import ask
from app.utils.vector_cache import VectorCache

cwd_bp = Blueprint("cwd_bp", __name__, template_folder="templates", static_folder="static", url_prefix="/cwd")

lock = threading.Lock()


@cwd_bp.route("/cwd_index")
def cwd_index():
    # Get the list of uploaded files for the current user
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
    VectorCache.load_user_vectors(current_user.id)
    return render_template("cwd.html", documents=documents_data)


@cwd_bp.route("/query", methods=["POST"])
def query_endpoint():
    client, error = initialize_openai_client(current_user.id)
    selected_docs = request.form.getlist("selected_docs")  # Assuming it's a list of document IDs
    print(selected_docs)
    query = request.form.get("query")
    # Document.query.filter_by(user_id=current_user.id).update({"selected": 0})
    if selected_docs:
        selected_docs_ids = [doc_id for doc_id in selected_docs]
        Document.query.filter(Document.id.in_(selected_docs_ids)).update({"selected": 1}, synchronize_session="fetch")

    db.session.commit()  # Commit the changes to the database

    def generate():
        for content in ask(query, client):
            yield content

    response = current_app.response_class(stream_with_context(generate()), content_type="text/plain")
    response.headers["X-Accel-Buffering"] = "no"
    return response
