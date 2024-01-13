from flask import Blueprint, request, jsonify, send_from_directory, url_for
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.util.audio_util import (
    generate_speech,
    transcribe_audio,
    translate_audio,
    segment_large_audio,
    fictitious_prompt_from_instruction,
)
from app.util.forms_util import TtsForm, TranscriptionForm, TranslationForm
from app.util.session_util import initialize_openai_client
import os

audio_bp = Blueprint("audio", __name__, url_prefix="/audio")


@audio_bp.route("/tts-preferences", methods=["GET", "POST"])
@login_required
def tts_preferences():
    form = TtsForm()
    if form.validate_on_submit():
        client, error = initialize_openai_client(current_user.id)
        if error:
            return jsonify({"status": "error", "message": error})



        response = generate_speech(
            client,
            model=form.model.data,
            voice=form.voice.data,
            input_text=form.input.data,
            response_format=form.response_format.data,
            speed=form.speed.data,
        )

        if "error" in response:
            return jsonify({"status": "error", "message": response["error"]})

        audio_content = response.get("data")
        filename = secure_filename(f"tts_output.{form.response_format.data}")
        filepath = os.path.join(current_user.get_audio_folder(), filename)
        with open(filepath, "wb") as f:
            f.write(audio_content)

        download_url = url_for("audio.download_file", filename=filename, _external=True)
        return jsonify({"status": "success", "download_url": download_url})

    return jsonify({"status": "error", "message": "Invalid form data"})


@audio_bp.route("/transcription", methods=["GET", "POST"])
@login_required
def transcription():
    form = TranscriptionForm()
    if form.validate_on_submit():
        client, error = initialize_openai_client(current_user.id)
        if error:
            return jsonify({"status": "error", "message": error})

        audio_file = form.file.data
        filename = secure_filename(audio_file.filename)
        filepath = os.path.join(current_user.get_audio_folder(), filename)
        audio_file.save(filepath)

        segment_filepaths = segment_large_audio(filepath)
        transcriptions = []
        if form.generate.prompt.data:
            prompt = fictitious_prompt_from_instruction(
                client, form.generate.prompt.data
            )
        else:
            prompt = form.prompt.data
        for segment_filepath in segment_filepaths:
            response = transcribe_audio(
                client,
                file_path=segment_filepath,
                model=form.model.data,
                language=form.language.data,
                prompt=prompt,
                response_format=form.response_format.data,
                temperature=form.temperature.data,
            )

            if "error" in response:
                return jsonify({"status": "error", "message": response["error"]})

            transcriptions.append(response.get("text"))

        full_transcription = " ".join(transcriptions)
        transcription_filename = secure_filename(f"transcription_{filename}.txt")
        transcription_filepath = os.path.join(
            current_user.get_audio_folder(), transcription_filename
        )
        with open(transcription_filepath, "w") as f:
            f.write(full_transcription)

        download_url = url_for(
            "audio.download_file", filename=transcription_filename, _external=True
        )
        return jsonify({"status": "success", "download_url": download_url})

    return jsonify({"status": "error", "message": "Invalid form data"})


@audio_bp.route("/translation", methods=["GET", "POST"])
@login_required
def translation():
    form = TranslationForm()
    if form.validate_on_submit():
        client, error = initialize_openai_client(current_user.id)
        if error:
            return jsonify({"status": "error", "message": error})

        audio_file = form.file.data
        filename = secure_filename(audio_file.filename)
        filepath = os.path.join(current_user.get_audio_folder(), filename)
        audio_file.save(filepath)

        segment_filepaths = segment_large_audio(filepath)
        translations = []
        if form.generate_prompt.data:
            prompt = fictitious_prompt_from_instruction(
                client, form.generate_prompt.data
            )
        else:
            prompt = form.prompt.data
        for segment_filepath in segment_filepaths:
            response = translate_audio(
                client,
                file_path=segment_filepath,
                model=form.model.data,
                prompt=prompt,
                response_format=form.response_format.data,
                temperature=form.temperature.data,
            )

            if "error" in response:
                return jsonify({"status": "error", "message": response["error"]})

            translations.append(response.get("text"))

        full_translation = " ".join(translations)
        translation_filename = secure_filename(f"translation_{filename}.txt")
        translation_filepath = os.path.join(
            current_user.get_audio_folder(), translation_filename
        )
        with open(translation_filepath, "w") as f:
            f.write(full_translation)

        download_url = url_for(
            "audio.download_file", filename=translation_filename, _external=True
        )
        return jsonify({"status": "success", "download_url": download_url})

    return jsonify({"status": "error", "message": "Invalid form data"})


@audio_bp.route("/download/<filename>")
@login_required
def download_file(filename):
    directory = current_user.get_audio_folder()
    return send_from_directory(directory, filename, as_attachment=True)
