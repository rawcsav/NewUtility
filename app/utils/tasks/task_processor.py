import time
from app import create_app
from app.models.task_models import (
    Task,
    TTSTask,
    TranscriptionTask,
    TranslationTask,
    EmbeddingTask,
    ImageTask,
    DeletionTask,
)
from app.utils.tasks.audio_task import process_tts_task, process_transcription_task, process_translation_task
from app.utils.tasks.deletion_task import process_deletion_task
from app.utils.tasks.embedding_task import process_embedding_task
from app.utils.tasks.image_task import process_image_task


def process_tasks():
    app = create_app()
    with app.app_context():
        while True:
            # Fetch and process different types of tasks
            pending_tasks = Task.query.filter_by(status="pending").all()

            for task in pending_tasks:
                if isinstance(task, TTSTask):
                    process_tts_task(task.id)
                elif isinstance(task, TranscriptionTask):
                    process_transcription_task(task.id)
                elif isinstance(task, TranslationTask):
                    process_translation_task(task.id)
                elif isinstance(task, EmbeddingTask):
                    process_embedding_task(task.id)
                elif isinstance(task, ImageTask):
                    process_image_task(task.id)
                elif isinstance(task, DeletionTask):
                    process_deletion_task(task.id)

            # Pause before checking for more tasks
            time.sleep(10)


if __name__ == "__main__":
    process_tasks()
