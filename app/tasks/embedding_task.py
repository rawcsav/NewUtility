import os


from app.models.embedding_models import Document, DocumentChunk
from app.models.task_models import Task, EmbeddingTask
from app.modules.auth.auth_util import task_client
from app.modules.embedding.embedding_util import (
    extract_text_from_file,
    split_text,
    get_embedding_batch,
    store_embeddings,
)
from app.tasks.task_logging import setup_logging
from app.utils.task_util import make_session
from app.utils.usage_util import embedding_cost
from app import socketio
from app.tasks.celery_task import celery

# Configure logging for the embedding task
logger = setup_logging()


def process_document(session, embedding_task, user_id):
    try:
        # Emit progress update
        socketio.emit(
            "task_progress",
            {"task_id": embedding_task.task_id, "message": f"Extracting text from {embedding_task.title}..."},
            room=str(user_id),
            namespace="/embedding",
        )

        text_pages = extract_text_from_file(embedding_task.temp_path)
        chunks, chunk_pages, total_tokens, chunk_token_counts = split_text(text_pages, embedding_task.chunk_size)

        new_document = Document(
            user_id=user_id,
            task_id=embedding_task.task_id,
            title=embedding_task.title,
            author=embedding_task.author,
            total_tokens=total_tokens,
        )
        session.add(new_document)
        session.flush()

        # Emit progress update
        socketio.emit(
            "task_progress",
            {"task_id": embedding_task.task_id, "message": f"Processing document chunks for {embedding_task.title}..."},
            room=str(user_id),
            namespace="/embedding",
        )

        for i, (chunk_content, pages) in enumerate(zip(chunks, chunk_pages)):
            pages_str = None  # Default to None
            if pages is not None:  # Correctly check if pages is not None
                # Convert each integer page number to a string before joining
                pages_str = ",".join(map(str, pages))
            chunk = DocumentChunk(
                document_id=new_document.id,
                chunk_index=i,
                content=chunk_content,
                tokens=chunk_token_counts[i],
                pages=pages_str,
            )
            session.add(chunk)
        session.commit()
        # Emit progress update
        socketio.emit(
            "task_progress",
            {"task_id": embedding_task.task_id, "message": f"Generating embeddings for {embedding_task.title}..."},
            room=str(user_id),
            namespace="/embedding",
        )

        client, key_id, error = task_client(session, user_id)
        if error:
            raise Exception(error)
        embeddings = get_embedding_batch(chunks, client)
        store_embeddings(session, new_document.id, embeddings, user_id)
        embedding_cost(session=session, user_id=user_id, api_key_id=key_id, input_tokens=total_tokens)
        socketio.emit(
            "task_progress",
            {"task_id": embedding_task.task_id, "message": f"Calculating cost of {embedding_task.title}..."},
            room=str(user_id),
            namespace="/embedding",
        )
        # Emit final completion event with document details
        socketio.emit(
            "task_complete",
            {
                "task_id": embedding_task.task_id,
                "message": f"Embedding task for {embedding_task.title} has completed.",
                "status": "completed",
                "document": {
                    "title": embedding_task.title,
                    "author": embedding_task.author,
                    "chunk_count": len(chunks),
                    "document_id": new_document.id,
                    "page_amount": len(text_pages),
                    "total_tokens": total_tokens,
                },
            },
            room=str(user_id),
            namespace="/embedding",
        )

    except Exception as e:
        logger.info(f"Error processing document {embedding_task.id}: {e}")
        os.remove(embedding_task.temp_path)
        # Emit error event
        socketio.emit(
            "task_update",
            {"task_id": embedding_task.task_id, "status": "error", "error": str(e)},
            room=str(user_id),
            namespace="/embedding",
        )
        raise e


@celery.task(time_limit=200)
def process_embedding_task(task_id):
    session = make_session()
    embedding_task = None
    task = None
    try:
        logger.info(f"Retrieving embedding task with ID '{task_id}'")
        embedding_task = session.query(EmbeddingTask).filter_by(task_id=task_id).first()

        if not embedding_task:
            raise ValueError(f"EmbeddingTask for task ID '{task_id}' not found")
        task = session.query(Task).filter_by(id=task_id).one()
        print(task.user_id)
        print(embedding_task.author)
        process_document(session, embedding_task, user_id=task.user_id)
        # Success and completion updates are now handled within process_document
        return True
    except Exception as e:
        session.rollback()
        socketio.emit(
            "task_update",
            {"task_id": task_id, "status": "error", "error": str(e)},
            room=str(task.user_id),
            namespace="/embedding",
        )
        return False
    finally:
        if embedding_task:
            try:
                if os.path.exists(embedding_task.temp_path):
                    os.remove(embedding_task.temp_path)
            except Exception as e:
                pass
        session.remove()
