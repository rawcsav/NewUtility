from app.models.task_models import Task, TTSTask, TranscriptionTask, TranslationTask
from app.modules.audio.audio_util import (
    generate_speech,
    preprocess_audio,
    transcribe_audio,
    user_subdirectory,
    translate_audio,
)
from app.modules.auth.auth_util import task_client
from app.utils.tasks.task_logging import setup_logging

logger = setup_logging()


def process_tts(session, tts_task, user_id):
    try:
        logger.info(f"Starting TTS processing for task_id={tts_task.task_id}")
        client, key_id, error = task_client(session, user_id)
        if error:
            raise Exception(error)

        tts_filepath = generate_speech(
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
        return tts_filepath
    except Exception as e:
        logger.error(f"Error during TTS processing for task_id={tts_task.task_id}: {e}")
        raise e


def process_tts_task(session, task_id):
    task = session.query(Task).get(task_id)
    tts_task = session.query(TTSTask).filter_by(task_id=task_id).first()

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


def process_translation(session, translation_task, user_id):
    try:
        logger.info(f"Starting translation processing for task_id={translation_task.task_id}")
        client, key_id, error = task_client(session, user_id)
        if error:
            raise Exception(error)

        input_filename = translation_task.input_filename
        download_dir = user_subdirectory(user_id)

        # Preprocess audio and translate
        segment_filepaths = preprocess_audio(input_filename, download_dir)
        file_id = translate_audio(
            session=session,
            user_id=user_id,
            api_key_id=key_id,
            client=client,
            file_paths=segment_filepaths,
            input_filename=input_filename,
            model=translation_task.model,
            prompt=translation_task.prompt,
            response_format=translation_task.response_format,
            temperature=translation_task.temperature,
            task_id=translation_task.task_id,
        )
        logger.info(f"Translation processing completed for task_id={translation_task.task_id}")
        return file_id
    except Exception as e:
        logger.error(f"Error during translation processing for task_id={translation_task.task_id}: {e}")
        raise e


def process_translation_task(session, task_id):
    task = session.query(Task).get(task_id)
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


def process_transcription(session, transcription_task, user_id):
    try:
        logger.info(f"Starting transcription processing for task_id={transcription_task.task_id}")
        client, key_id, error = task_client(session, user_id)
        if error:
            raise Exception(error)

        input_filename = transcription_task.input_filename
        download_dir = user_subdirectory(user_id)
        segment_filepaths = preprocess_audio(input_filename, download_dir)
        file_id = transcribe_audio(
            session=session,
            user_id=user_id,
            api_key_id=key_id,
            client=client,
            file_paths=segment_filepaths,
            input_filename=input_filename,
            model=transcription_task.model,
            prompt=transcription_task.prompt,
            response_format=transcription_task.response_format,
            temperature=transcription_task.temperature,
            language=transcription_task.language,
            task_id=transcription_task.task_id,
        )
        logger.info(f"Transcription processing completed for task_id={transcription_task.task_id}")
        return file_id
    except Exception as e:
        logger.error(f"Error during transcription processing for task_id={transcription_task.task_id}: {e}")
        raise e


def process_transcription_task(session, task_id):
    task = session.query(Task).get(task_id)
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
