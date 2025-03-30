from typing import List
import numpy as np
import openai
from flask_login import current_user
from openai import RateLimitError
from app import db, socketio
from app.models.chat_models import ChatPreferences
from app.models.embedding_models import DocumentChunk, Document, ModelContextWindow
from app.utils.vector_cache import VectorCache


def find_relevant_sections(user_id, query_embedding, user_preferences):
    context_window_size = 120000
    max_sections = user_preferences.top_k
    threshold = user_preferences.threshold

    document_chunks_with_details = (
        db.session.query(
            DocumentChunk.id,
            Document.title,
            Document.author,
            DocumentChunk.pages,
            DocumentChunk.content,  # Include the chunk content
            DocumentChunk.tokens,
        )
        .join(Document)
        .filter(Document.user_id == user_id, Document.selected == 1)
        .all()
    )

    # Get the IDs of the chunks for the current user's documents
    subset_ids = [str(chunk.id) for chunk in document_chunks_with_details]

    # Get a descending list of similarities for the subset using the MIPS naive method
    similarities = VectorCache.mips_naive(query_embedding, subset_ids)

    # Filter out any similarities below the threshold
    filtered_similarities = [(chunk_id, sim) for chunk_id, sim in similarities if sim >= threshold]

    # Select chunks based on the max number of sections, token limit, and similarity threshold
    selected_chunks = []
    sections_appended = 0
    current_tokens = 0

    for chunk_id, similarity in filtered_similarities:
        if sections_appended >= max_sections:
            break

        chunk = next((c for c in document_chunks_with_details if str(c.id) == chunk_id), None)
        if chunk and current_tokens + chunk.tokens <= context_window_size:
            selected_chunks.append(
                (chunk.id, chunk.title, chunk.author, chunk.pages, chunk.content, chunk.tokens, similarity)
            )
            current_tokens += chunk.tokens
            sections_appended += 1
        elif chunk:
            break

    return selected_chunks


def get_embedding(text: str, client: openai.OpenAI, model="text-embedding-3-large", **kwargs) -> List[float]:
    response = client.embeddings.create(input=text, model=model, **kwargs)
    embedding = response.data[0].embedding
    if len(embedding) != 3072:
        raise ValueError(f"Expected embedding dimension to be 3072, but got {len(embedding)}")
    return embedding


def append_knowledge_context(user_query, user_id, client):
    query_embedding = get_embedding(user_query, client)
    query_vector = np.array(query_embedding, dtype=np.float32)
    user_preferences = db.session.query(ChatPreferences).filter_by(user_id=user_id).one()

    relevant_sections = find_relevant_sections(user_id, query_vector, user_preferences=user_preferences)

    context = ""
    chunk_associations = []
    doc_pages = {}  # Dictionary to hold document ID and a list of pages

    preface = f"Use the below textual excerpts to answer the subsequent question. If the answer cannot be found in the provided text, say as such but still do your best to provide the most factual, nuanced assessment possible.\n\nQuestion: {user_query}\n\nText excerpts:\n\n"

    context = preface
    chunk_associations = []
    for chunk_id, title, author, pages, chunk_content, tokens, similarity in relevant_sections:
        context_parts = []
        if title:
            context_parts.append(f"Title: {title}")
        if author:
            context_parts.append(f"Author: {author}")
        if title not in doc_pages:
            doc_pages[title] = {}  # Dictionary to hold page numbers and their similarity scores
        if pages:
            # Split the pages string by the comma
            page_numbers = pages.split(",")
            for page in page_numbers:
                # Add each page number only if it exists and has not been included yet
                if page and page not in doc_pages[title]:
                    doc_pages[title][page] = similarity
                else:
                    # Update the similarity score if the page already exists and has a higher similarity
                    if similarity > doc_pages[title][page]:
                        doc_pages[title][page] = similarity
        context_parts.append(f"Content:\n{chunk_content}")

        context += "\n".join(context_parts) + "\n\n"

        chunk_associations.append((chunk_id, similarity))

    # Sort the pages in doc_pages by their page numbers
    for title in doc_pages:
        sorted_pages = sorted(doc_pages[title].items(), key=lambda x: int(x[0]))
        doc_pages[title] = [page for page, _ in sorted_pages]

    return context, chunk_associations, doc_pages


def chat_completion_with_retry(messages, model, client, temperature, top_p):
    return client.chat.completions.create(
        model=model, messages=messages, temperature=temperature, top_p=top_p, stream=True
    )


def ask(query, images, client, model: str = "gpt-4-0125-preview"):
    modified_query, chunk_associations, doc_pages = append_knowledge_context(query, current_user.id, client)
    preferences = ChatPreferences.query.filter_by(user_id=current_user.id).first()
    temperature = preferences.temperature
    top_p = preferences.top_p
    system_prompt = preferences.cwd_system_prompt
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": modified_query},
                *[{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image}"}} for image in images],
            ],
        },
    ]

    try:
        documents_used_summary = ""
        for title, pages in doc_pages.items():
            if pages:
                documents_used_summary += f"{title}: Pages {', '.join(map(str, sorted(pages)))}, "
                print(f"{title}: Pages {', '.join(map(str, sorted(pages)))}")
            else:
                documents_used_summary += f"{title}, "
        socketio.emit(
            "documents_used", {"message": documents_used_summary}, room=str(current_user.id), namespace="/cwd"
        )

        for part in chat_completion_with_retry(messages, model, client, temperature, top_p):
            content = part.choices[0].delta.content
            if content:
                yield content
    except RateLimitError as e:
        pass
