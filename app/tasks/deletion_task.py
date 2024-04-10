import os
from app.tasks.celery_task import celery
from app.models.audio_models import TranslationJob, TTSJob, TranscriptionJob
from app.models.chat_models import Conversation
from app.models.embedding_models import Document
from app.models.image_models import GeneratedImage, MessageImages
from app.models.task_models import Task, DeletionTask
from app.models.user_models import UserAPIKey, User
from app.modules.user.user_util import get_user_gen_img_directory, get_user_chat_img_directory, \
    get_user_audio_directory, get_user_upload_directory
from app.utils.logging_util import configure_logging
from app.utils.task_util import make_session

logger = configure_logging()


def delete_local_files(entity_id, entity_type, user_id):
    # Map entity types to their directory retrieval functions
    dir_retrieval_funcs = {
        "generated_images": get_user_gen_img_directory,
        "message_images": get_user_chat_img_directory,
        "tts_jobs": get_user_audio_directory,
        "transcription_jobs": get_user_audio_directory,
        "translation_jobs": get_user_audio_directory,
        "documents": get_user_upload_directory
    }

    # Retrieve the directory based on the entity type
    dir_to_check = dir_retrieval_funcs.get(entity_type, lambda user_id: None)(user_id)
    if not dir_to_check:
        return
    for root, dirs, files in os.walk(dir_to_check):
        for filename in files:
            if entity_id in filename:
                file_path = os.path.join(root, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)


def delete_entity(session, entity_type, entity_id, user_id):
    model_classes = {
        "translation_jobs": TranslationJob,
        "tts_jobs": TTSJob,
        "transcription_jobs": TranscriptionJob,
        "conversations": Conversation,
        "documents": Document,
        "user_api_keys": UserAPIKey,
        "generated_images": GeneratedImage,
        "message_images": MessageImages,
        "user": User,
    }

    model_class = model_classes.get(entity_type)
    if not model_class:
        raise ValueError(f"Unknown entity type: {entity_type}")

    entity = session.query(model_class).get(entity_id)
    if not entity:
        raise ValueError(f"Entity of type '{entity_type}' with ID '{entity_id}' not found")

    try:
        delete_local_files(entity_id, entity_type, user_id)
        session.delete(entity)
        session.commit()
    except Exception as e:
        raise e


@celery.task(time_limit=60)
def process_deletion_task(task_id):
    session = make_session()
    try:
        task = session.query(Task).filter_by(id=task_id).one()
        if not task:
            raise ValueError(f"Task with ID '{task_id}' not found")

        deletion_task = session.query(DeletionTask).filter_by(task_id=task_id).first()
        if not deletion_task:
            raise ValueError(f"DeletionTask for task ID '{task_id}' not found")

        delete_entity(session, deletion_task.entity_type, deletion_task.entity_id, task.user_id)
        return True
    except Exception as e:
        session.rollback()
        logger.error(f"Error processing deletion task {task_id}: {e}")
        return False
    finally:
        session.remove()  # Dispose of the session correctly
