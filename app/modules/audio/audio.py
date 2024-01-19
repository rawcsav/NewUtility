import os
from markdown2 import markdown

from flask import Blueprint, jsonify, url_for, render_template, send_file, current_app, request
from flask_login import login_required, current_user
from openai import InternalServerError
from werkzeug.utils import secure_filename
from app import db
from app.models.audio_models import TTSPreferences, WhisperPreferences, TTSJob, TranscriptionJob, TranslationJob
from app.models.task_models import Task, TTSTask, TranslationTask, TranscriptionTask
from app.modules.audio.audio_util import (
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
from app.utils.forms_util import TtsForm, TranscriptionForm, TranslationForm, TtsPreferencesForm, WhisperPreferencesForm
from app.modules.auth.auth_util import initialize_openai_client

audio_bp = Blueprint("audio_bp", __name__, template_folder="templates", static_folder="static", url_prefix="/audio")


@audio_bp.route("/", methods=["GET"])
@login_required
def audio_center():
    # Fetch user preferences
    user_tts_preferences = TTSPreferences.query.filter_by(user_id=current_user.id).first()
    user_whisper_preferences = WhisperPreferences.query.filter_by(user_id=current_user.id).first()

    # Instantiate forms with user preferences
    tts_preferences_form = TtsPreferencesForm(obj=user_tts_preferences)
    whisper_preferences_form = WhisperPreferencesForm(obj=user_whisper_preferences)

    tts_form = TtsForm()
    transcription_form = TranscriptionForm()
    translation_form = TranslationForm()
    markdown_file_path = os.path.join(current_app.root_path, audio_bp.static_folder, "audio.md")

    with open(markdown_file_path, "r") as file:
        markdown_content = file.read()
    docs_content = markdown(markdown_content)
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
        tooltip=docs_content,
    )


@audio_bp.route("/tts_preferences", methods=["POST"])
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


@audio_bp.route("/whisper_preferences", methods=["POST"])
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


@audio_bp.route("/generate_tts", methods=["GET", "POST"])
@login_required
def generate_tts():
    form = TtsForm()
    if request.method == "POST" and form.validate():
        try:
            preferences = get_tts_preferences(current_user.id)

            # Create a new Task for TTS generation
            new_task = Task(type="TTS", status="pending", user_id=current_user.id)
            db.session.add(new_task)
            db.session.flush()

            # Create a new TTSTask
            new_tts_task = TTSTask(
                task_id=new_task.id,
                model=preferences["model"],
                voice=preferences["voice"],
                input_text=form.input.data,
                response_format=preferences["response_format"],
                speed=preferences["speed"],
            )
            db.session.add(new_tts_task)
            db.session.commit()

            return jsonify({"status": "success", "task_id": new_task.id})

        except Exception as e:
            db.session.rollback()
            return jsonify({"status": "error", "message": str(e)})

    # For GET requests or failed POST validations, return an appropriate JSON response
    return jsonify({"status": "error", "message": "Invalid request or form data"})


@audio_bp.route("/transcription", methods=["GET", "POST"])
@login_required
def transcription():
    form = TranscriptionForm()
    if form.validate_on_submit():
        user_id = current_user.id
        preferences = get_whisper_preferences(user_id)
        client, error = initialize_openai_client(user_id)
        if error:
            return jsonify({"status": "error", "message": error})
        download_dir = user_subdirectory(user_id)
        audio_file = form.file.data
        filename = secure_filename(audio_file.filename)
        filepath = os.path.join(download_dir, filename)
        audio_file.save(filepath)
        prompt = determine_prompt(client, form.data)

        new_task = Task(type="Transcription", status="pending", user_id=user_id)
        new_transcription_task = TranscriptionTask(
            task_id=new_task.id,
            input_filename=filename,
            model=preferences["model"],
            prompt=prompt,
            response_format=preferences["response_format"],
            temperature=preferences["temperature"],
            language=preferences["language"],
        )
        db.session.add_all([new_task, new_transcription_task])
        db.session.commit()

        return jsonify({"status": "success", "task_id": new_task.id})

    return jsonify({"status": "error", "message": "Invalid form submission"})


@audio_bp.route("/translation", methods=["GET", "POST"])
@login_required
def translation():
    form = TranslationForm()
    if form.validate_on_submit():
        user_id = current_user.id
        preferences = get_whisper_preferences(user_id)
        client, error = initialize_openai_client(user_id)
        if error:
            return jsonify({"status": "error", "message": error})
        download_dir = user_subdirectory(user_id)
        audio_file = form.file.data
        filename = secure_filename(audio_file.filename)
        filepath = os.path.join(download_dir, filename)
        audio_file.save(filepath)
        prompt = determine_prompt(client, form.data)

        new_task = Task(type="Translation", status="pending", user_id=user_id)
        new_translation_task = TranslationTask(
            task_id=new_task.id,
            input_filename=filename,
            model=preferences["model"],
            prompt=prompt,
            response_format=preferences["response_format"],
            temperature=preferences["temperature"],
        )
        db.session.add_all([new_task, new_translation_task])
        db.session.commit()

        return jsonify({"status": "success", "task_id": new_task.id})

    return jsonify({"status": "error", "message": "Invalid form submission"})


@audio_bp.route("/download_tts/<filename>")
@login_required
def download_tts(filename):
    user_dir = user_subdirectory(current_user.id)

    secure_filename_path = secure_filename(filename)

    file_path = os.path.join(user_dir, secure_filename_path)

    if os.path.isfile(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return jsonify({"status": "error", "message": "File not found"}), 404


@audio_bp.route("/download_whisper/<job_id>")
@login_required
def download_whisper(job_id):
    job = TranscriptionJob.query.get(job_id) or TranslationJob.query.get(job_id)
    if not job or job.user_id != current_user.id:
        return jsonify({"status": "error", "message": "File not found or access denied"}), 404

    concatenated_content = job.final_content
    file_extension = {"json": "json", "verbose_json": "json", "text": "txt", "srt": "srt", "vtt": "vtt"}.get(
        job.response_format, "txt"
    )
    user_directory = user_subdirectory(current_user.id)
    file_path = save_file_to_disk(concatenated_content, file_extension, job_id, user_directory)
    try:
        return send_file(file_path, as_attachment=True)
    finally:
        try:
            os.remove(file_path)
        except Exception as error:
            raise InternalServerError(f"Unable to delete file: {error}")
