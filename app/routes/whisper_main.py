import glob
import os
import threading
from time import sleep

from flask import (
    Blueprint,
    request,
    get_flashed_messages,
    render_template,
    flash,
    redirect,
    url_for,
    session,
    Response,
    send_from_directory,
    jsonify,
)
from werkzeug.utils import secure_filename

from app.config import SUPPORTED_FORMATS, MAX_CONTENT_LENGTH, MAX_AUDIO_FILE_SIZE
from app.util.audio_util import transcribe_file, TranscriptionFailedException
from app.util.docauth_util import check_api_key
from pathlib import Path

bp = Blueprint("whisper_main", __name__)

lock = threading.Lock()


@bp.route("/whisper_index", methods=["GET"])
def whisper_index():
    messages = get_flashed_messages()
    return render_template("whisper_index.html", messages=messages)


@bp.route("/upload_audio", methods=["POST"])
def upload_audio():
    if "audio_file" not in request.files:
        return jsonify({"error": "No file part"})

    file = request.files["audio_file"]

    if file.filename == "":
        return jsonify({"error": "No selected file"})

    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(session["WHISPER_UPLOAD_DIR"], filename)
        file.save(file_path)
        session["file_path"] = file_path  # Save file path in session
        return jsonify({"success": True, "filename": filename})  # Return filename
    else:
        return jsonify({"error": "File type not supported"})


@bp.route("/transcribe", methods=["POST"])
def transcribe():
    api_key = session.get("api_key")
    use_timestamps = request.form.get("use_timestamps")
    language = request.form.get("language")
    translate = request.form.get("translate") == "yes"
    file_path = session.get("file_path")  # Get file path from session
    # Validate API key
    if not check_api_key(api_key):
        flash("Invalid API key! Please check your API key and try again.", "error")

    if not file_path:
        flash("Please upload an audio file.", "error")

    os.makedirs(session["WHISPER_UPLOAD_DIR"], exist_ok=True)
    whisper_directory = session["WHISPER_UPLOAD_DIR"]

    with lock:
        try:
            txt_file_name = transcribe_file(
                file_path,
                whisper_directory,
                api_key,
                use_timestamps,
                language,
                translate,
            )
        except TranscriptionFailedException as e:
            flash(str(e), "error")
            sleep(10)
            return redirect(url_for("whisper_main.whisper_index"))

        transcribed_file_name = os.path.join(whisper_directory, txt_file_name)

        download_url = url_for("whisper_main.download", filename=transcribed_file_name)

        # Return JSON response
        return jsonify(success=True, download_url=download_url)


@bp.route("/download/<path:filename>", methods=["GET"])
def download(filename):
    # Get the project's root directory
    project_root_directory = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../..")
    )

    # Construct the absolute path
    file_path = os.path.join(project_root_directory, filename)

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    # Extract the directory from the absolute file path to send it using send_from_directory
    directory, file_name = os.path.split(file_path)
    response = send_from_directory(directory, file_name, as_attachment=True)

    return response
