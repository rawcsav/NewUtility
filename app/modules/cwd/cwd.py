import os
import threading

import openai
import pandas as pd
from flask import Blueprint, render_template, request, jsonify, session
from flask_login import current_user
from werkzeug.utils import secure_filename

from app.modules.auth.auth_util import initialize_openai_client
from app.modules.cwd.cwd_util import (
    add_embeddings_to_df,
    gather_text_sections,
    extract_text_from_file,
    get_uploaded_files_for_user,
)
from app.modules.cwd.cwd_util import allowed_file, ask
import os
from flask import request, stream_with_context, Blueprint, current_app


cwd_bp = Blueprint("cwd_bp", __name__, template_folder="templates", static_folder="static", url_prefix="/cwd")

lock = threading.Lock()


@cwd_bp.route("/cwd_index")
def cwd_index():
    user_upload_dir = os.path.join(current_app.config["CHAT_UPLOAD_DIR"], str(current_user.id))
    os.makedirs(user_upload_dir, exist_ok=True)

    # Get the list of uploaded files for the current user
    uploaded_files = get_uploaded_files_for_user()

    return render_template("cwd.html", uploaded_files=uploaded_files)


@cwd_bp.route("/upload", methods=["POST"])
def upload_file():
    client, error = initialize_openai_client(current_user.id)

    response = {"status": "success", "messages": []}

    CHAT_UPLOAD_DIR = os.path.join(current_app.config["CHAT_UPLOAD_DIR"], str(current_user.id))
    EMBED_DATA_PATH = os.path.join(CHAT_UPLOAD_DIR, "embed_data.json")

    os.makedirs(CHAT_UPLOAD_DIR, exist_ok=True)

    if "file" not in request.files:
        response["status"] = "error"
        response["messages"].append("No file part in the request.")
        return jsonify(response), 400

    uploaded_files = request.files.getlist("file")
    if not uploaded_files:
        response["status"] = "error"
        response["messages"].append("No file selected for uploading.")
        return jsonify(response), 400

    new_files = []

    for file in uploaded_files:
        secure_file_name = secure_filename(file.filename)
        print(secure_file_name)
        if not file or file.content_length > 512 or not allowed_file(secure_file_name):
            response["messages"].append(f"File {secure_file_name} is either too large or not of an allowed type.")
            continue
        if file and allowed_file(secure_file_name):
            CHAT_UPLOAD_DIR = os.path.join(current_app.config["CHAT_UPLOAD_DIR"], str(current_user.id))
            filename = os.path.join(CHAT_UPLOAD_DIR, secure_file_name)
            file.save(filename)

            # Convert to .txt if it's a pdf or docx
            if filename.endswith(".pdf") or filename.endswith(".docx"):
                txt_filepath = extract_text_from_file(filename)
                if txt_filepath:
                    filename = txt_filepath
                else:
                    response["messages"].append(f"File {secure_file_name} conversion to .txt failed.")
                    continue

            new_files.append(os.path.basename(filename))
            response["messages"].append(f"File {os.path.basename(filename)} processed successfully.")

    try:
        df_new = gather_text_sections(CHAT_UPLOAD_DIR)
        df_new = add_embeddings_to_df(df_new, client)
    except Exception as e:
        response["status"] = "error"
        response["messages"].append(f"Error generating embeddings for {secure_file_name}: {str(e)}")

    with lock:
        if os.path.exists(EMBED_DATA_PATH) and os.path.getsize(EMBED_DATA_PATH) > 0:
            df_existing = pd.read_json(EMBED_DATA_PATH, orient="split")
        else:
            df_existing = pd.DataFrame()

        if df_existing.empty:
            df_combined = df_new
        else:
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)

    df_combined.to_json(EMBED_DATA_PATH, orient="split")

    return jsonify(response)


@cwd_bp.route("/remove_file", methods=["DELETE"])
def remove_file():
    file_name = request.args.get("fileName", default=None)
    file_name_df = os.path.splitext(file_name)[0]
    CHAT_UPLOAD_DIR = os.path.join(current_app.config["CHAT_UPLOAD_DIR"], str(current_user.id))
    EMBED_DATA_PATH = os.path.join(CHAT_UPLOAD_DIR, "embed_data.json")

    if not file_name:
        return jsonify({"status": "error", "message": "No file name provided"}), 400

    file_path = os.path.join(CHAT_UPLOAD_DIR, file_name)
    if not os.path.exists(file_path):
        return jsonify({"status": "error", "message": "File does not exist"}), 404

    os.remove(file_path)

    # If you need to update JSON data
    if os.path.exists(file_path):
        return jsonify({"status": "error", "message": "Failed to delete file"}), 500

    with lock:
        if os.path.exists(EMBED_DATA_PATH) and os.path.getsize(EMBED_DATA_PATH) > 0:
            df_existing = pd.read_json(EMBED_DATA_PATH, orient="split")
            df_existing = df_existing[df_existing["title"] != file_name_df]
            if not df_existing.empty:  # Only write if DataFrame is not empty
                df_existing.to_json(EMBED_DATA_PATH, orient="split")

    uploaded_files = get_uploaded_files_for_user()
    if file_name in uploaded_files:
        uploaded_files.remove(file_name)

    return jsonify({"status": "success", "message": f"File {file_name} deleted successfully"})


@cwd_bp.route("/query", methods=["POST"])
def query_endpoint():
    client, error = initialize_openai_client(current_user.id)
    CHAT_UPLOAD_DIR = os.path.join(current_app.config["CHAT_UPLOAD_DIR"], str(current_user.id))
    EMBED_DATA_PATH = os.path.join(CHAT_UPLOAD_DIR, "embed_data.json")

    query = request.form.get("query")
    selected_docs = request.form.get("selected_docs")

    if selected_docs:
        selected_docs = selected_docs.split(",")

    df_path = EMBED_DATA_PATH
    if df_path and os.path.exists(df_path):
        df = pd.read_json(df_path, orient="split")
    else:
        return "Error: Data not found.", 400

    def generate():
        for content in ask(query, df, client, specific_documents=selected_docs):
            yield content

    response = current_app.response_class(stream_with_context(generate()), content_type="text/plain")
    response.headers["X-Accel-Buffering"] = "no"
    return response
