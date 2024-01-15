import os
import tempfile
from datetime import datetime, timedelta

from flask import (
    Blueprint,
    jsonify,
    url_for,
    render_template,
    send_file,
    current_app,
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.database import (
    TTSPreferences,
    WhisperPreferences,
    TTSJob,
    TranslationJob,
    TranscriptionJob,
)
from app.util.audio_util import (
    generate_speech,
    transcribe_audio,
    translate_audio,
    determine_prompt,
    user_subdirectory,
    get_whisper_preferences,
    preprocess_audio,
    get_tts_preferences,
    save_file_to_disk,
)
from app.util.forms_util import (
    TtsForm,
    TranscriptionForm,
    TranslationForm,
    TtsPreferencesForm,
    WhisperPreferencesForm,
)
from app.util.session_util import initialize_openai_client

bp = Blueprint("audio", __name__, url_prefix="/audio")


@bp.route("/audio", methods=["GET"])
@login_required
def audio_center():
    # Fetch user preferences
    user_tts_preferences = TTSPreferences.query.filter_by(
        user_id=current_user.id
    ).first()
    user_whisper_preferences = WhisperPreferences.query.filter_by(
        user_id=current_user.id
    ).first()

    # Instantiate forms with user preferences
    tts_preferences_form = TtsPreferencesForm(obj=user_tts_preferences)
    whisper_preferences_form = WhisperPreferencesForm(obj=user_whisper_preferences)

    tts_form = TtsForm()
    transcription_form = TranscriptionForm()
    translation_form = TranslationForm()

    # Other required data
    tts_jobs = TTSJob.query.filter_by(user_id=current_user.id).all()
    translation_jobs = TranslationJob.query.filter_by(user_id=current_user.id).all()
    transcription_jobs = TranscriptionJob.query.filter_by(user_id=current_user.id).all()
    return render_template(
        "audio.html",
        tts_preferences_form=tts_preferences_form,
        user_tts_preferences=user_tts_preferences,
        whisper_preferences_form=whisper_preferences_form,
        user_whisper_preferences=user_whisper_preferences,
        tts_form=tts_form,
        transcription_form=transcription_form,
        translation_form=translation_form,
        TTSJobs=tts_jobs,
        TranslationJobs=translation_jobs,
        TranscriptionJobs=transcription_jobs,
    )


@bp.route("/tts_preferences", methods=["POST"])
@login_required
def tts_preferences():
    tts_prefs = TTSPreferences.query.filter_by(user_id=current_user.id).first()
    form = TtsPreferencesForm(obj=tts_prefs)

    if form.validate_on_submit():
        tts_prefs.model = form.model.data
        tts_prefs.voice = form.voice.data
        tts_prefs.response_format = form.response_format.data
        tts_prefs.speed = form.speed.data
        db.session.commit()

        return jsonify(
            {
                "status": "success",
                "message": "Your TTS preferences have been updated.",
                "preferences": {
                    "model": tts_prefs.model,
                    "voice": tts_prefs.voice,
                    "response_format": tts_prefs.response_format,
                    "speed": tts_prefs.speed,
                },
            }
        )
    else:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "There was an error updating your TTS preferences.",
                    "errors": form.errors,
                }
            ),
            400,
        )


@bp.route("/whisper_preferences", methods=["POST"])
@login_required
def whisper_preferences():
    whisper_prefs = WhisperPreferences.query.filter_by(user_id=current_user.id).first()
    form = WhisperPreferencesForm(obj=whisper_prefs)

    if form.validate_on_submit():
        whisper_prefs.model = form.model.data
        whisper_prefs.language = form.language.data
        whisper_prefs.response_format = form.response_format.data
        whisper_prefs.temperature = form.temperature.data
        db.session.commit()

        return jsonify(
            {
                "status": "success",
                "message": "Your Whisper preferences have been updated.",
                "preferences": {
                    "model": whisper_prefs.model,
                    "language": whisper_prefs.language,
                    "response_format": whisper_prefs.response_format,
                    "temperature": whisper_prefs.temperature,
                },
            }
        )
    else:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "There was an error updating your Whisper preferences.",
                    "errors": form.errors,
                }
            ),
            400,
        )


@bp.route("/generate_tts", methods=["GET", "POST"])
@login_required
def generate_tts():
    form = TtsForm()
    if form.validate_on_submit():
        client, error = initialize_openai_client(current_user.id)
        if error:
            return jsonify({"status": "error", "message": error})
        preferences = get_tts_preferences(current_user.id)
        filepath, filename = generate_speech(
            client,
            model=preferences["model"],
            voice=preferences["voice"],
            input_text=form.input.data,
            response_format=preferences["response_format"],
            speed=preferences["speed"],
        )
        return jsonify(
            {
                "status": "success",
                "download_url": url_for("audio.download_tts", filename=filename),
            }
        )


@bp.route("/transcription", methods=["GET", "POST"])
@login_required
def transcription():
    form = TranscriptionForm()
    if form.validate_on_submit():
        user_id = current_user.id
        download_dir = user_subdirectory(user_id)
        client, error = initialize_openai_client(user_id)
        if error:
            return jsonify({"status": "error", "message": error})
        preferences = get_whisper_preferences(user_id)
        audio_file = form.file.data
        filename = secure_filename(audio_file.filename)
        filepath = os.path.join(download_dir, filename)
        audio_file.save(filepath)
        segment_filepaths = preprocess_audio(filepath, download_dir)
        prompt = determine_prompt(client, form.data)
        temperature = preferences.get("temperature", 0)
        job_id = transcribe_audio(
            client,
            file_paths=segment_filepaths,
            input_filename=filename,
            model=preferences["model"],
            prompt=prompt,
            response_format=preferences["response_format"],
            temperature=temperature,
            language=preferences["language"],
        )
        return jsonify(
            {
                "status": "success",
                "download_url": url_for("audio.download_whisper", job_id=job_id),
            }
        )


@bp.route("/translation", methods=["GET", "POST"])
@login_required
def translation():
    form = TranslationForm()
    if form.validate_on_submit():
        user_id = current_user.id
        download_dir = user_subdirectory(user_id)
        client, error = initialize_openai_client(user_id)
        if error:
            return jsonify({"status": "error", "message": error})

        preferences = get_whisper_preferences(user_id)
        audio_file = form.file.data
        filename = secure_filename(audio_file.filename)
        filepath = os.path.join(download_dir, filename)
        audio_file.save(filepath)
        segment_filepaths = preprocess_audio(filepath, download_dir)
        prompt = determine_prompt(client, form.data)
        job_id = translate_audio(
            client,
            file_paths=segment_filepaths,
            input_filename=filename,
            model=preferences["model"],
            prompt=prompt,
            response_format=preferences["response_format"],
            temperature=preferences["temperature"],
        )
        return jsonify(
            {
                "status": "success",
                "download_url": url_for("audio.download_whisper", job_id=job_id),
            }
        )


@bp.route("/download_tts/<filename>")
@login_required
def download_tts(filename):
    user_dir = user_subdirectory(current_user.id)

    secure_filename_path = secure_filename(filename)

    file_path = os.path.join(user_dir, secure_filename_path)

    if os.path.isfile(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return jsonify({"status": "error", "message": "File not found"}), 404


@bp.route("/download_whisper/<job_id>")
@login_required
def download_whisper(job_id):
    job = TranscriptionJob.query.get(job_id) or TranslationJob.query.get(job_id)
    if not job or job.user_id != current_user.id:
        return (
            jsonify({"status": "error", "message": "File not found or access denied"}),
            404,
        )
    if (
        job.download_url
        and job.download_timestamp
        and datetime.utcnow() - job.download_timestamp < timedelta(hours=24)
    ):
        return send_file(job.download_url, as_attachment=True)

    print("making final_content into download")
    concatenated_content = job.final_content
    file_extension = {
        "json": "json",
        "verbose_json": "json",
        "text": "txt",
        "srt": "srt",
        "vtt": "vtt",
    }.get(job.response_format, "txt")
    user_directory = user_subdirectory(current_user.id)
    file_path = save_file_to_disk(
        concatenated_content, file_extension, job_id, user_directory
    )
    job.download_url = file_path
    job.download_timestamp = datetime.utcnow()
    db.session.commit()

    return send_file(file_path, as_attachment=True)
