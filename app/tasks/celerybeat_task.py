import os
from datetime import datetime, timedelta
from glob import glob

from app.models.audio_models import TTSJob, TranslationJob, TranscriptionJob
from app.models.embedding_models import Document
from app.models.task_models import Task, EmbeddingTask
from app.modules.user.user_util import get_user_audio_directory
from app.tasks.celery_task import celery
from app.utils.logging_util import configure_logging
from app.utils.task_util import make_session

logger = configure_logging()


@celery.task()
def cleanup_documents():
    session = make_session()
    try:
        now = datetime.utcnow()
        # Fetch both new and soft-deleted documents in one query
        all_documents = session.query(Document).filter(
            (Document.created_at <= now - timedelta(minutes=15)) |
            (Document.created_at >= now - timedelta(hours=3)) |
            (Document.delete == True)
        ).all()

        for document in all_documents:
            document_task_id = document.task_id
            embedding_task = session.query(EmbeddingTask).filter_by(task_id=document_task_id).first()
            if embedding_task and os.path.exists(embedding_task.temp_path):
                os.remove(embedding_task.temp_path)
                logger.info(f"Removed file at {embedding_task.temp_path}")

            if document.delete:
                session.delete(document)

        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Error processing deletion task: {e}")
        return False
    finally:
        session.remove()  # Dispose of the session correctly


@celery.task()
def cleanup_tts():
    session = make_session()
    try:
        now = datetime.utcnow()
        # Fetch both new (over 24 hours old) and soft-deleted TTS jobs in one go
        all_tts_jobs = session.query(TTSJob).filter(
            (TTSJob.created_at <= now - timedelta(hours=24)) | (TTSJob.delete == True)
        ).all()

        for tts in all_tts_jobs:
            tts_output_path = os.path.join(get_user_audio_directory(tts.user_id), tts.output_filename)
            if os.path.exists(tts_output_path):
                os.remove(tts_output_path)
                logger.info(f"Removed file at {tts_output_path}")
            session.delete(tts)

        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Error processing deletion task: {e}")
        return False
    finally:
        session.remove()  # Dispose of the session correctly

@celery.task()
def cleanup_transcription():
    session = make_session()
    try:
        now = datetime.utcnow()
        transcription_jobs = session.query(TranscriptionJob).filter(
            TranscriptionJob.created_at <= now - timedelta(minutes=15),
            TranscriptionJob.created_at >= now - timedelta(hours=3)
        ).all()

        soft_deleted_transcription_jobs = session.query(TranscriptionJob).filter(
            (TranscriptionJob.created_at <= now - timedelta(hours=48)) |
            (TranscriptionJob.delete == True)
        ).all()


        unique_task_ids = {job.task_id for job in transcription_jobs + soft_deleted_transcription_jobs}

        for task_id in unique_task_ids:
            for file in glob(f"*{task_id}*.*"):
                os.remove(file)
                logger.info(f"Removed file {file}")

            soft_deleted_jobs = [job for job in soft_deleted_transcription_jobs if job.task_id == task_id]
            for job in soft_deleted_jobs:
                session.delete(job)

        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Error processing deletion task: {e}")
        return False
    finally:
        session.remove()  # Dispose of the session correctly



@celery.task()
def cleanup_translation():
    session = make_session()
    try:
        now = datetime.utcnow()
        translation_jobs = session.query(TranslationJob).filter(
            TranslationJob.created_at <= now - timedelta(minutes=15),
            TranslationJob.created_at >= now - timedelta(hours=3)
        ).all()

        soft_deleted_translation_jobs = session.query(TranslationJob).filter(
            (TranslationJob.created_at <= now - timedelta(hours=8)) |
            (TranslationJob.delete == True)
        ).all()


        unique_task_ids = {job.task_id for job in translation_jobs + soft_deleted_translation_jobs}

        for task_id in unique_task_ids:
            for file in glob(f"*{task_id}*.*"):
                os.remove(file)
                logger.info(f"Removed file {file}")

            soft_deleted_jobs = [job for job in soft_deleted_translation_jobs if job.task_id == task_id]
            for job in soft_deleted_jobs:
                session.delete(job)

        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Error processing deletion task: {e}")
        return False
    finally:
        session.remove()  # Dispose of the session correctly
