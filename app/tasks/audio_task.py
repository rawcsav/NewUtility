import os
from app import socketio
from app.tasks.celery_task import celery
from app.modules.user.user_util import get_user_audio_directory
from app.models.task_models import Task, TTSTask, TranscriptionTask, TranslationTask
from app.modules.audio.audio_util import generate_speech, preprocess_audio, transcribe_audio, translate_audio
from app.modules.auth.auth_util import task_client
from app.utils.logging_util import configure_logging
from app.utils.task_util import make_session

logger = configure_logging()

def process_tts(session, tts_task, user_id):
    try:
        logger.info(f"Starting TTS processing for task_id={tts_task.task_id}")
        client, key_id, error = task_client(session, user_id)
        if error:
            raise Exception(error)
        socketio.emit(
            "task_progress",
            {"task_id": tts_task.task_id, "message": "Generating speech..."},
            room=str(user_id),
            namespace="/audio",
        )
        tts_filepath, job_id = generate_speech(
            session=session,
            client=client,
            api_key_id=key_id,
            user_id=user_id,
            model=tts_task.model,
            voice=tts_task.voice,
            input_text=tts_task.input_text,
            response_format=tts_task.response_format,
            speed=tts_task.speed,
            task_id=tts_task.task_id,
        )
        logger.info(f"TTS processing completed for task_id={tts_task.task_id}")
        socketio.emit(
            "task_complete",
            {
                "task_id": tts_task.task_id,
                "message": "TTS processing completed!",
                "status": "completed",
                "job_type": "tts",
                "job_details": {
                    "id": job_id,
                    "output_filename": os.path.basename(tts_filepath),
                    "model": tts_task.model,
                    "voice": tts_task.voice,
                    "speed": tts_task.speed,
                    "created_at": "Just now",
                },
            },
            room=str(user_id),
            namespace="/audio",
        )
        return tts_filepath
    except Exception as e:
        socketio.emit(
            "task_update",
            {"task_id": tts_task.task_id, "status": "error", "error": str(e)},
            room=str(user_id),
            namespace="/audio",
        )
        logger.error(f"Error during TTS processing for task_id={tts_task.task_id}: {e}")
        raise e


@celery.task(time_limit=200)
def process_tts_task(task_id):
    session = make_session()
    try:
        task = session.query(Task).filter_by(id=task_id).one()
        tts_task = session.query(TTSTask).filter_by(task_id=task_id).first()
        socketio.emit(
            "task_progress",
            {"task_id": task.id, "message": f"Beginning TTS task..."},
            room=str(task.user_id),
            namespace="/audio",
        )
        if task and tts_task and task.status:
            try:
                success = process_tts(session, tts_task, user_id=task.user_id)
                if success:
                    logger.info(f"Task {task_id} status updated to completed")
                    return True
                else:
                    logger.error(f"Task {task_id} failed during processing")
                    return False
            except Exception as e:
                session.rollback()
                logger.error(f"Error processing task {task_id}: {e}")
                return False
        else:
            logger.error(f"Task {task_id} is not pending or task not found")
            return False
    finally:
        session.remove()  # Dispose of the session correctly


def process_translation(session, translation_task, user_id):
    try:
        logger.info(f"Starting translation processing for task_id={translation_task.task_id}")

        client, key_id, error = task_client(session, user_id)
        if error:
            raise Exception(error)

        task_id = translation_task.task_id
        download_dir = get_user_audio_directory(user_id)
        filepath = translation_task.input_filename

        socketio.emit(
            "task_progress",
            {
                "task_id": translation_task.task_id,
                "message": f"Beginning translation of {translation_task.original_filename}...",
            },
            room=str(user_id),
            namespace="/audio",
        )
        segment_filepaths = preprocess_audio(filepath, download_dir, user_id, task_id)
        file_id, total_duration = translate_audio(
            session=session,
            user_id=user_id,
            api_key_id=key_id,
            client=client,
            file_paths=segment_filepaths,
            original_filename=translation_task.original_filename,
            input_filename=filepath,
            model=translation_task.model,
            prompt=translation_task.prompt,
            response_format=translation_task.response_format,
            temperature=translation_task.temperature,
            task_id=translation_task.task_id,
        )
        logger.info(f"Translation processing completed for task_id={task_id}")
        socketio.emit(
            "task_complete",
            {
                "task_id": translation_task.task_id,
                "message": f"Translation processing for {translation_task.original_filename} completed!",
                "status": "completed",
                "job_type": "translation",
                "job_details": {
                    "id": file_id,
                    "model": translation_task.model,
                    "prompt": translation_task.prompt,
                    "response_format": translation_task.response_format,
                    "temperature": translation_task.temperature,
                    "original_filename": translation_task.original_filename,
                    "created_at": "Just now",
                },
            },
            room=str(user_id),
            namespace="/audio",
        )
        return file_id
    except Exception as e:
        socketio.emit(
            "task_update",
            {"task_id": translation_task.task_id, "status": "error", "error": str(e)},
            room=str(user_id),
            namespace="/audio",
        )
        logger.error(f"Error during translation processing for task_id={translation_task.task_id}: {e}")
        raise e


@celery.task(time_limit=300)
def process_translation_task(task_id):
    session = make_session()
    try:
        task = session.query(Task).filter_by(id=task_id).one()
        translation_task = session.query(TranslationTask).filter_by(task_id=task_id).first()

        if task and translation_task:
            try:
                success = process_translation(session, translation_task, user_id=task.user_id)
                if success:
                    logger.info(f"Task {task_id} status updated to completed")
                    return True
                else:
                    logger.error(f"Task {task_id} failed during processing")
                    return False
            except Exception as e:
                session.rollback()
                logger.error(f"Error processing task {task_id}: {e}")
                return False
        else:
            logger.error(f"Task {task_id} is not pending or task not found")
            return False
    finally:
        session.remove()  # Dispose of the session correctly


def process_transcription(session, transcription_task, user_id):
    try:
        logger.info(f"Starting transcription processing for task_id={transcription_task.task_id}")
        client, key_id, error = task_client(session, user_id)
        if error:
            raise Exception(error)

        task_id = transcription_task.task_id
        download_dir = get_user_audio_directory(user_id)
        filepath = transcription_task.input_filename

        segment_filepaths = preprocess_audio(filepath, download_dir, user_id, task_id)
        file_id, total_duration = transcribe_audio(
            session=session,
            user_id=user_id,
            api_key_id=key_id,
            client=client,
            file_paths=segment_filepaths,
            input_filename=filepath,
            original_filename=transcription_task.original_filename,
            model=transcription_task.model,
            prompt=transcription_task.prompt,
            response_format=transcription_task.response_format,
            temperature=transcription_task.temperature,
            language=transcription_task.language,
            task_id=task_id,
        )
        logger.info(f"Transcription processing completed for task_id={task_id}")
        socketio.emit(
            "task_complete",
            {
                "task_id": task_id,
                "message": f"Transcription processing for {os.path.basename(transcription_task.original_filename)} completed!",
                "status": "completed",
                "job_type": "transcription",
                "job_details": {
                    "id": file_id,
                    "model": transcription_task.model,
                    "language": transcription_task.language,
                    "prompt": transcription_task.prompt,
                    "response_format": transcription_task.response_format,
                    "temperature": transcription_task.temperature,
                    "original_filename": transcription_task.original_filename,
                    "created_at": "Just now",
                },
            },
            room=str(user_id),
            namespace="/audio",
        )
        return file_id
    except Exception as e:
        socketio.emit(
            "task_update",
            {"task_id": transcription_task.task_id, "status": "error", "error": str(e)},
            room=str(user_id),
            namespace="/audio",
        )
        logger.error(f"Error during transcription processing for task_id={transcription_task.task_id}: {e}")
        raise e


@celery.task(time_limit=300)
def process_transcription_task(task_id):
    session = make_session()
    try:
        task = session.query(Task).filter_by(id=task_id).one()
        transcription_task = session.query(TranscriptionTask).filter_by(task_id=task_id).first()
        if task and transcription_task:
            try:
                success = process_transcription(session, transcription_task, user_id=task.user_id)
                if success:
                    logger.info(f"Task {task_id} status updated to completed")
                    return True
                else:
                    logger.error(f"Task {task_id} failed during processing")
                    return False
            except Exception as e:
                session.rollback()
                logger.error(f"Error processing task {task_id}: {e}")
                return False
        else:
            logger.error(f"Task {task_id} is not pending or task not found")
            return False
    finally:
        session.remove()  # Dispose of the session correctly
