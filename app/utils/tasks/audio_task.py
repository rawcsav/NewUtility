from app import create_app, db
from app.models.task_models import Task, TTSTask, TranscriptionTask, TranslationTask
from app.modules.audio.audio_util import (
    generate_speech,
    preprocess_audio,
    transcribe_audio,
    user_subdirectory,
    translate_audio,
)
from app.modules.auth.auth_util import initialize_openai_client


def process_tts(tts_task, user_id):
    try:
        client, error = initialize_openai_client(user_id)
        if error:
            raise Exception(error)

        generate_speech(
            client,
            model=tts_task.model,
            voice=tts_task.voice,
            input_text=tts_task.input_text,
            response_format=tts_task.response_format,
            speed=tts_task.speed,
            task_id=tts_task.task_id,
        )

    except Exception as e:
        print(f"Error processing TTS task {tts_task.id}: {e}")
        tts_task.task.status = "failed"
        db.session.commit()
        return

    tts_task.task.status = "completed"
    db.session.commit()


def process_tts_task(task_id):
    app = create_app()
    with app.app_context():
        task = Task.query.get(task_id)
        tts_task = TTSTask.query.filter_by(task_id=task.id).first()

        if task and tts_task and task.status == "pending":
            process_tts(tts_task=tts_task, user_id=task.user_id)


def process_translation(translation_task, user_id):
    try:
        client, error = initialize_openai_client(user_id)
        if error:
            raise Exception(error)

        input_filename = translation_task.input_filename
        download_dir = user_subdirectory(user_id)

        # Preprocess audio and translate
        segment_filepaths = preprocess_audio(input_filename, download_dir)
        translate_audio(
            client,
            file_paths=segment_filepaths,
            input_filename=input_filename,
            model=translation_task.model,
            prompt=translation_task.prompt,
            response_format=translation_task.response_format,
            temperature=translation_task.temperature,
            task_id=translation_task.track_id,
        )

    except Exception as e:
        print(f"Error processing translation task {translation_task.id}: {e}")
        translation_task.task.status = "failed"
        db.session.commit()
        return

    translation_task.task.status = "completed"
    db.session.commit()


def process_translation_task(task_id):
    app = create_app()
    with app.app_context():
        task = Task.query.get(task_id)
        translation_task = TranslationTask.query.filter_by(task_id=task_id).first()

        if task and translation_task and task.status == "pending":
            process_translation(translation_task=translation_task, user_id=task.user_id)


def process_transcription(transcription_task, user_id):
    try:
        # Extracting task details
        client, error = initialize_openai_client(user_id)
        if error:
            raise Exception(error)
        input_filename = transcription_task.input_filename
        download_dir = user_subdirectory(user_id)
        segment_filepaths = preprocess_audio(input_filename, download_dir)
        transcribe_audio(
            client,
            file_paths=segment_filepaths,
            input_filename=input_filename,
            model=transcription_task.model,
            prompt=transcription_task.prompt,
            response_format=transcription_task.response_format,
            temperature=transcription_task.temperature,
            language=transcription_task.language,
            task_id=transcription_task.track_id,
        )

    except Exception as e:
        print(f"Error processing transcription task {transcription_task.id}: {e}")
        transcription_task.task.status = "failed"
        db.session.commit()
        return

    transcription_task.task.status = "completed"
    db.session.commit()


def process_transcription_task(task_id):
    app = create_app()
    with app.app_context():
        task = Task.query.get(task_id)
        transcription_task = TranscriptionTask.query.filter_by(task_id=task_id).first()

        if task and transcription_task and task.status == "pending":
            process_transcription(transcription_task=transcription_task, user_id=task.user_id)
