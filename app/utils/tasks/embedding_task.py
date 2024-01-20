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
from app.utils.tasks.task_logging import setup_logging

from app.utils.usage_util import embedding_cost

# Configure logging for the embedding task
logger = setup_logging()


def process_document(session, embedding_task, user_id):
    try:
        print("working")
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

        for i, (chunk_content, pages) in enumerate(zip(chunks, chunk_pages)):
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
        client, key_id, error = task_client(session, user_id)
        if error:
            raise Exception(error)
        embeddings = get_embedding_batch(chunks, client)
        store_embeddings(session, new_document.id, embeddings, user_id)
        embedding_cost(session=session, user_id=user_id, api_key_id=key_id, input_tokens=total_tokens)
    except Exception as e:
        logger.info(f"Error processing document {embedding_task.id}: {e}")
        os.remove(embedding_task.temp_path)
        raise e


def process_embedding_task(session, task_id):
    try:
        logger.info(f"Retrieving embedding task with ID '{task_id}'")
        embedding_task = session.query(EmbeddingTask).filter_by(task_id=task_id).first()

        if not embedding_task:
            raise ValueError(f"EmbeddingTask for task ID '{task_id}' not found")
        task = session.query(Task).filter_by(id=task_id).one()
        print(task)

        process_document(session, embedding_task, user_id=task.user_id)
        logger.info(f"Embedding task {task_id} processed successfully")
        return True
    except Exception as e:
        logger.error(f"Error processing embedding task {task_id}: {e}")
        return False
