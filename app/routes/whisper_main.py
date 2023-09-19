import glob
import os
import threading

from flask import (
    Blueprint,
    request,
    get_flashed_messages,
    render_template,
    flash,
    redirect,
    url_for,
    session,
    send_from_directory,
)
from werkzeug.utils import secure_filename

from app.config import SUPPORTED_FORMATS, MAX_CONTENT_LENGTH
from app.util.audio_util import transcribe_files, TranscriptionFailedException
from app.util.docauth_util import check_api_key

bp = Blueprint("whisper_main", __name__)

lock = threading.Lock()


@bp.route("/whisper_index", methods=["GET"])
def whisper_index():
    messages = get_flashed_messages()
    return render_template("whisper_index.html", messages=messages)


@bp.route("/transcribe", methods=["POST"])
def transcribe():
    audio_files = request.files.getlist("audio_files")
    api_key = request.form.get("api_key")
    use_timestamps = request.form.get("use_timestamps") == "yes"
    language = request.form.get("language")
    translate = request.form.get("translate") == "yes"

    # Validate API key
    if not check_api_key(api_key):
        flash("Invalid API key! Please check your API key and try again.", "error")
        return redirect(url_for("whisper_main.whisper_index"))

    if not audio_files or not api_key:
        flash("Please upload audio files and provide an API key.", "error")
        return redirect(url_for("whisper_main.whisper_index"))

    valid_files = [
        file
        for file in audio_files
        if file.filename.endswith(SUPPORTED_FORMATS)
        and file.content_length <= MAX_CONTENT_LENGTH
    ]
    if not valid_files:
        flash("No supported audio files selected!", "error")
        return redirect(url_for("whisper_main.whisper_index"))

    os.makedirs(session["WHISPER_UPLOAD_DIR"], exist_ok=True)
    output_directory = session["WHISPER_UPLOAD_DIR"]
    input_directory = session["WHISPER_UPLOAD_DIR"]

    with lock:
        for uploaded_file in valid_files:
            filename = secure_filename(uploaded_file.filename)
            file_path = os.path.join(input_directory, filename)
            uploaded_file.save(file_path)

        try:
            transcribe_files(
                input_directory,
                output_directory,
                api_key,
                use_timestamps,
                language,
                translate,
            )
        except TranscriptionFailedException as e:
            flash(str(e), "error")
            return redirect(url_for("whisper_main.whisper_index"))

    return redirect(url_for("whisper_main.results", output_dir=output_directory))


@bp.route("/results", methods=["GET"])
def results():
    output_directory = session["WHISPER_UPLOAD_DIR"]

    if not output_directory:
        flash("Missing output directory.", "error")
        return redirect(url_for("whisper_main.whisper_index"))

    try:
        # Get a list of all .txt files in the directory
        txt_files = glob.glob(os.path.join(output_directory, "*.txt"))

        # Get the project's root directory
        project_root_directory = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../..")
        )

        # Get the relative paths of the .txt files
        txt_files_relative = [
            os.path.relpath(txt_file, project_root_directory) for txt_file in txt_files
        ]

        # Print the list of .txt files
        print(f"Text Files: {txt_files_relative}")
    except FileNotFoundError:
        flash("Output directory not found.", "error")
        return redirect(url_for("whisper_main.whisper_index"))

    return render_template(
        "whisper_results.html",
        files=txt_files_relative,
        output_directory=output_directory,
    )


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
