import os
from celery import shared_task
from app.models.audio_models import TranslationJob, TTSJob, TranscriptionJob
from app.models.chat_models import Conversation
from app.models.embedding_models import Document
from app.models.image_models import GeneratedImage, MessageImages
from app.models.task_models import Task, DeletionTask
from app.models.user_models import UserAPIKey, User
from app.modules.user.user_util import get_user_gen_img_directory, get_user_chat_img_directory, get_user_audio_directory
from app.tasks.task_logging import setup_logging
from app.utils.task_util import make_session

logger = setup_logging()


def delete_local_files(entity_id, entity_type, user_id):
    if entity_type == "generated_images":
        dir_to_check = get_user_gen_img_directory(user_id)
    elif entity_type == "message_images":
        dir_to_check = get_user_chat_img_directory(user_id)
    elif entity_type in ["tts_jobs", "transcription_jobs", "translation_jobs"]:
        dir_to_check = get_user_audio_directory(user_id)
    else:
        return  # Return if the entity type does not match

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
    except Exception as e:
        raise e


@shared_task
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
