import os
from datetime import datetime, timedelta
from app.models.embedding_models import Document
from app.models.task_models import Task, EmbeddingTask
from app.tasks.celery_task import celery
from app.tasks.task_logging import setup_logging
from app.utils.task_util import make_session

logger = setup_logging()

@celery.task()
def cleanup_documents():
    session = make_session()
    try:
        now = datetime.utcnow()
        # Find documents older than 15 minutes and newer than last 12 hours
        new_documents = session.query(Document).filter(
            Document.created_at <= now - timedelta(minutes=15),
            Document.created_at >= now - timedelta(hours=13)
        ).all()

        for document in new_documents:
            document_task_id = document.task_id
            embedding_task = session.query(EmbeddingTask).filter_by(task_id=document_task_id).first()
            if os.path.exists(embedding_task.temp_path):
                os.remove(embedding_task.temp_path)
                print(f"Removed file at {embedding_task.temp_path}")

        # Handle soft-deleted documents
        soft_deleted_documents = session.query(Document).filter(Document.delete == True).all()

        for document in soft_deleted_documents:
            document_task_id = document.task_id
            embedding_task = session.query(EmbeddingTask).filter_by(task_id=document_task_id).first()
            if os.path.exists(embedding_task.temp_path):
                os.remove(embedding_task.temp_path)
                print(f"Removed file at {embedding_task.temp_path}")
            session.delete(document)
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Error processing deletion task: {e}")
        return False
    finally:
        session.remove()  # Dispose of the session correctly