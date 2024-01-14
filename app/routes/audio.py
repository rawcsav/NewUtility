import os

from flask import (
    Blueprint,
    jsonify,
    send_from_directory,
    url_for,
    render_template,
send_file,
)
from flask_login import login_required, current_user
from werkzeug.security import safe_join
from werkzeug.utils import secure_filename
from flask import request
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
    segment_audio,
    determine_prompt,
    user_subdirectory,
    get_whisper_preferences,
    convert_format,
    trim_start,
    get_tts_preferences,
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

    # Other forms without pre-filled data
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


@bp.route("/tts-preferences", methods=["POST"])
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


@bp.route("/whisper-preferences", methods=["POST"])
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


@bp.route("/generate-tts", methods=["GET", "POST"])
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
                "download_url": url_for(
                    "audio.download_file", filename=filename
                ),
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
        segment_filepaths = segment_audio(filepath)
        prompt = determine_prompt(client, form.data)
        filepath = transcribe_audio(
            client,
            file_paths=segment_filepaths,
            model=preferences["model"],
            prompt=prompt,
            response_format=preferences["response_format"],
            temperature=preferences["temperature"],
            language=preferences["language"],
        )
        return jsonify(
            {
                "status": "success",
                "download_url": url_for(
                    "bp.download_file", filename=os.path.basename(filepath)
                ),
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
        mp3_filepath = convert_format(filepath)
        trimmed_mp3_filepath = trim_start(mp3_filepath)
        segment_filepaths = segment_audio(trimmed_mp3_filepath)
        prompt = determine_prompt(client, form.data)
        filepath = translate_audio(
            client,
            file_paths=segment_filepaths,
            model=preferences["model"],
            prompt=prompt,
            response_format=preferences["response_format"],
            temperature=preferences["temperature"],
        )
        return jsonify(
            {
                "status": "success",
                "download_url": url_for(
                    "bp.download_file", filename=os.path.basename(filepath)
                ),
            }
        )


@bp.route("/download/<filename>")
@login_required
def download_file(filename):
    download_dir = user_subdirectory(current_user.id)
    secure_path = os.path.join(download_dir, filename)
    print(secure_path)
    return send_file(secure_path, as_attachment=True)
