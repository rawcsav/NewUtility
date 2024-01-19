import os

from flask import current_app

from app import db, create_app
from app.models.audio_models import TranslationJob, TTSJob, TranscriptionJob
from app.models.chat_models import Conversation
from app.models.embedding_models import Document
from app.models.image_models import GeneratedImage, MessageImages
from app.models.user_models import UserAPIKey, User


def delete_local_files(entity_id, entity_type):
    if entity_type == "GeneratedImage":
        dir_to_check = current_app.config["USER_IMAGE_DIRECTORY"]
    elif entity_type == "MessageImages":
        dir_to_check = current_app.config["CHAT_IMAGE_DIRECTORY"]
    elif entity_type in ["TTSJob", "TranscriptionJob", "TranslationJob"]:
        dir_to_check = current_app.config["USER_AUDIO_DIRECTORY"]
    else:
        return  # Return if the entity type does not match

    for filename in os.listdir(dir_to_check):
        if entity_id in filename:
            file_path = os.path.join(dir_to_check, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)


def delete_entity(entity_type, entity_id):
    model_classes = {
        "TranslationJob": TranslationJob,
        "TTSJob": TTSJob,
        "TranscriptionJob": TranscriptionJob,
        "Conversation": Conversation,
        "Document": Document,
        "UserAPIKey": UserAPIKey,
        "GeneratedImage": GeneratedImage,
        "MessageImages": MessageImages,
        "User": User,
    }

    model_class = model_classes.get(entity_type)

    if model_class:
        entity = model_class.query.with_deleted().get(entity_id)
        if entity:
            try:
                delete_local_files(entity_id, entity_type)
                db.session.delete(entity)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                raise e  # Optionally log this error or handle it as needed


def process_deletion_task(deletion_task):
    app = create_app()
    with app.app_context():
        try:
            delete_entity(deletion_task.entity_type, deletion_task.entity_id)
            deletion_task.task.status = "completed"
            db.session.commit()
        except Exception as e:
            deletion_task.task.status = "failed"
            db.session.commit()
