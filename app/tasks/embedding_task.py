import concurrent
from concurrent import futures
import os


from app.models.embedding_models import Document, DocumentChunk
from app.models.task_models import Task, EmbeddingTask
from app.modules.auth.auth_util import task_client, async_task_client
from app.modules.embedding.embedding_util import (
    get_embedding_batch,
    store_embeddings, TextSplitter, TextExtractor, extract_uuid_from_path,
)
from app.utils.logging_util import configure_logging
from app.utils.socket_util import emit_task_update
from app.utils.task_util import make_session
from app.utils.usage_util import embedding_cost
from app import socketio
from app.tasks.celery_task import celery

logger = configure_logging()


def process_document(session, embedding_task, user_id):
    try:
        emit_task_update("/embedding", embedding_task.task_id, user_id, "processing", f"Extracting text from {embedding_task.title}...")
        logger.info(f"Processing document {embedding_task.id}: {embedding_task.title}")

        extractor = TextExtractor(embedding_task.temp_path)
        text_pages = extractor.extract_text_from_file()

        client, key_id, error = task_client(session, user_id)
        if error:
            raise Exception(error)
        text_splitter = TextSplitter(max_tokens=embedding_task.chunk_size, client=client, use_gpt_preprocessing=embedding_task.advanced_preprocessing)
        logger.info(f"Splitting text into chunks of {embedding_task.chunk_size} tokens")
        for text, page_number in text_pages:
            text_splitter.add_text(text, page_number)

        # Finalize text splitting and get results
        chunks, chunk_pages, total_tokens, chunk_token_counts = text_splitter.finalize()
        file_uuid = extract_uuid_from_path(embedding_task.temp_path)

        new_document = Document(
            id=file_uuid,
            user_id=user_id,
            task_id=embedding_task.task_id,
            title=embedding_task.title,
            author=embedding_task.author,
            total_tokens=total_tokens,
        )
        session.add(new_document)
        session.flush()

        # Emit progress update for processing document chunks
        emit_task_update("/embedding", embedding_task.task_id, user_id, "processing", f"Processing document chunks for {embedding_task.title}...")
        # Process chunks as before
        for i, (chunk_content, pages) in enumerate(zip(chunks, chunk_pages)):
            pages_str = None
            if pages is not None:
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
        emit_task_update("/embedding", embedding_task.task_id, user_id, "processing", f"Generating embeddings for {embedding_task.title}...")
        embeddings = get_embedding_batch(chunks, client)
        store_embeddings(session, new_document.id, embeddings, user_id)
        embedding_cost(session=session, user_id=user_id, api_key_id=key_id, input_tokens=total_tokens)
        emit_task_update("/embedding", embedding_task.task_id, user_id, "processing", f"Calculating cost of {embedding_task.title}...")
        final_page_count = extractor.last_page_number
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
                    "page_amount": final_page_count,
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
        emit_task_update("/embedding", embedding_task.task_id, user_id, "error", f"Error: {str(e)}")
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
        process_document(session, embedding_task, user_id=task.user_id)
        # Success and completion updates are now handled within process_document
        return True
    except Exception as e:
        session.rollback()
        emit_task_update("/embedding", task_id, task.user_id, "error", f"Error: {str(e)}")
        return False
    finally:
        if embedding_task:
            try:
                if os.path.exists(embedding_task.temp_path):
                    os.remove(embedding_task.temp_path)
            except Exception as e:
                pass
        session.remove()

