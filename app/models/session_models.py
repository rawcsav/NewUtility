from sqlalchemy import func

from app import db
from app.models.audio_models import TTSJob, TranslationJob, TranscriptionJob
from app.models.chat_models import Conversation
from app.models.embedding_models import Document
from app.models.image_models import GeneratedImage, MessageImages
from app.models.mixins import generate_uuid
from sqlalchemy import event

from app.models.user_models import UserAPIKey, User


def after_update_listener(mapper, connection, target):
    if target.delete:
        deletion_task = Task(type="Deletion", status="pending", user_id=target.user_id)
        connection.execute(
            Task.__table__.insert(), type=deletion_task.type, status=deletion_task.status, user_id=deletion_task.user_id
        )

        task_id = connection.execute("SELECT LAST_INSERT_ID()").scalar()

        connection.execute(
            DeletionTask.__table__.insert(), task_id=task_id, entity_type=target.__tablename__, entity_id=target.id
        )


class Task(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    type = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(255), default="pending")
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"))
    input_params = db.Column(db.Text)
    result = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=False), default=func.now())
    updated_at = db.Column(db.DateTime(timezone=False), default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Task {self.id} {self.type} {self.status}>"


class DeletionTask(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    task_id = db.Column(db.String(36), db.ForeignKey("task.id"))  # Link to Task model
    entity_type = db.Column(db.String(255))  # Type of entity to delete (e.g., 'TTSJob', 'File')
    entity_id = db.Column(db.String(36))  # ID of the entity to delete


for cls in [
    GeneratedImage,
    MessageImages,
    TTSJob,
    TranslationJob,
    TranscriptionJob,
    Conversation,
    UserAPIKey,
    User,
    Document,
]:
    event.listen(cls, "after_update", after_update_listener)
