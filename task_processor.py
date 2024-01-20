from dotenv import load_dotenv
from app.models.task_models import Task
from app.utils.tasks.audio_task import process_tts_task, process_transcription_task, process_translation_task
from app.utils.tasks.deletion_task import process_deletion_task
from app.utils.tasks.embedding_task import process_embedding_task
from app.utils.tasks.image_task import process_image_task
import os
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.utils.tasks.task_logging import setup_logging
from sqlalchemy.exc import SQLAlchemyError
from app.utils.tunnel_util import get_tunnel

logger = setup_logging()


def find_and_mark_pending_task(Session):
    with Session() as session:  # Use Session() to create a new session instance
        pending_task = session.query(Task).filter_by(status="pending").first()
        if pending_task:
            pending_task.status = "processing"
            session.commit()  # Commit the changes within the session
            task_id = pending_task.id  # Store the id before closing the session
            return task_id  # Return the stored id
    return None


def process_task(Session, task_id, task_processors):
    with Session() as session:
        task = session.query(Task).filter_by(id=task_id).one()
        task_type = task.type.lower()
        try:
            if task_type in task_processors:
                logger.info(f"Starting processing task {task_id} of type '{task_type}'")
                success = task_processors[task_type](session, task_id)
                if success:
                    task.status = "completed"
                    logger.info(f"Task {task_id} completed successfully")
                else:
                    task.status = "failed"
                    logger.error(f"Task {task_id} failed during processing")
            else:
                logger.error(f"No processor defined for task type '{task.type}'")
                task.status = "failed"
        except Exception as e:
            logger.error(f"Error processing task {task_id} of type '{task_type}': {e}")
            task.status = "failed"
        finally:
            try:
                session.commit()
                logger.info(f"Task {task_id} status updated to '{task.status}'")
            except SQLAlchemyError as e:
                logger.error(f"Failed to commit task {task_id} status update: {e}")
                session.rollback()


if __name__ == "__main__":
    dotenv_path = ".env"
    print(dotenv_path)
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)

    FLASK_ENV = os.getenv("FLASK_ENV")
    SQL_USERNAME = os.getenv("SQL_USERNAME")
    SQL_PASSWORD = os.getenv("SQL_PASSWORD")
    SQL_DB_NAME = os.getenv("SQL_DB_NAME")

    if FLASK_ENV == "development":
        SSH_HOST = os.getenv("SSH_HOST")
        SSH_USER = os.getenv("SSH_USER")
        SSH_PASS = os.getenv("SSH_PASS")
        SQL_HOSTNAME = os.getenv("SQL_HOSTNAME")

        tunnel = get_tunnel(SSH_HOST, SSH_USER, SSH_PASS, SQL_HOSTNAME)
        connection_string = (
            f"mysql+pymysql://{SQL_USERNAME}:{SQL_PASSWORD}@localhost:{tunnel.local_bind_port}/{SQL_DB_NAME}"
        )
    else:
        # Direct connection for production environment
        SQL_HOSTNAME = os.getenv("SQL_HOSTNAME")
        connection_string = f"mysql+pymysql://{SQL_USERNAME}:{SQL_PASSWORD}@{SQL_HOSTNAME}/{SQL_DB_NAME}"

    engine = create_engine(connection_string)
    Session = sessionmaker(bind=engine)

    task_processors = {
        "tts": process_tts_task,
        "transcription": process_transcription_task,
        "translation": process_translation_task,
        "embedding": process_embedding_task,
        "image": process_image_task,
        "deletion": process_deletion_task,
    }

    while True:
        task_id = find_and_mark_pending_task(Session)
        if task_id:
            process_task(Session, task_id, task_processors)
        else:
            time.sleep(1)  # Sleep if no pending task is found
