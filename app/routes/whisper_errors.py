from flask import Blueprint, flash, redirect, url_for
from werkzeug.exceptions import RequestEntityTooLarge

from app.util.audio_util import TranscriptionFailedException

bp = Blueprint('errors', __name__)


@bp.errorhandler(RequestEntityTooLarge)
def file_too_large(e):
    flash("File is too large! Please upload files less than 50MB.", "error")
    return redirect(url_for('whisper_main.whisper_index'))


@bp.errorhandler(TranscriptionFailedException)
def handle_transcription_failed(e):
    flash("Transcription failed! Please check your API key and try again.", "error")
    return redirect(url_for('whisper_main.whisper_index'))


@bp.errorhandler(FileNotFoundError)
def handle_file_not_found(e):
    flash("File not found! Please check your uploaded files and try again.", "error")
    return redirect(url_for('whisper_main.whisper_index'))
