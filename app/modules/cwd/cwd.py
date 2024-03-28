import threading
from flask_login import current_user
from app import db
from app.models.chat_models import ChatPreferences
from app.models.embedding_models import Document
from app.modules.auth.auth_util import initialize_openai_client
from flask import request, stream_with_context, Blueprint, current_app, render_template
from app.modules.chat.chat import model_to_dict
from app.modules.cwd.cwd_util import ask
from app.utils.forms_util import UpdateDocPreferencesForm
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

    preferences = ChatPreferences.query.filter_by(user_id=current_user.id).first()
    if not preferences:
        preferences = ChatPreferences(user_id=current_user.id)
        db.session.add(preferences)
        db.session.commit()

    preferences_dict = model_to_dict(preferences)
    VectorCache.load_user_vectors(current_user.id)
    return render_template(
        "cwd.html", documents=documents_data, doc_preferences_form=UpdateDocPreferencesForm(data=preferences_dict)
    )


@cwd_bp.route("/query", methods=["POST"])
def query_endpoint():
    client, error = initialize_openai_client(current_user.id)
    query = request.form.get("query")
    db.session.commit()  # Commit the changes to the database

    def generate():
        for content in ask(query, client):
            yield content

    response = current_app.response_class(stream_with_context(generate()), content_type="text/event-stream")
    response.headers["X-Accel-Buffering"] = "no"
    return response
