import os
from app import create_app, db
from app.models.embedding_models import Document, DocumentChunk
from app.models.task_models import Task, EmbeddingTask
from app.modules.auth.auth_util import initialize_openai_client
from app.modules.embedding.embedding_util import (
    extract_text_from_file,
    split_text,
    get_embedding_batch,
    store_embeddings,
)
from app.utils.usage_util import embedding_cost


def process_document(embedding_task, user_id):
    try:
        # Processing steps for the individual document
        text_pages = extract_text_from_file(embedding_task.temp_path)
        chunks, chunk_pages, total_tokens, chunk_token_counts = split_text(text_pages, embedding_task.chunk_size)

        from datetime import datetime

        new_document = Document(
            user_id=embedding_task.user_id,
            task_id=embedding_task.task_id,
            title=embedding_task.title,
            author=embedding_task.author,
            total_tokens=total_tokens,
        )
        db.session.add(new_document)
        db.session.flush()

        for i, (chunk_content, pages) in enumerate(zip(chunks, chunk_pages)):
            pages_str = ",".join(map(str, pages))
            chunk = DocumentChunk(
                document_id=new_document.id,
                chunk_index=i,
                content=chunk_content,
                tokens=chunk_token_counts[i],
                pages=pages_str,
            )
            db.session.add(chunk)

        client, error = initialize_openai_client(user_id)
        if error:
            raise Exception(error)

        embeddings = get_embedding_batch(chunks, client)
        embedding_cost(total_tokens)
        store_embeddings(new_document.id, embeddings)
        db.session.commit()

        os.remove(embedding_task.temp_path)

    except Exception as e:
        db.session.rollback()
        print(f"Error processing document: {e}")


def process_embedding_task(task_id):
    app = create_app()
    with app.app_context():
        task = Task.query.get(task_id)
        embedding_task = EmbeddingTask.query.filter_by(task_id=task.id).first()

        if task and embedding_task and task.status == "pending":
            process_document(embedding_task=embedding_task, user_id=task.user_id)
            task.status = "completed"
            db.session.commit()
