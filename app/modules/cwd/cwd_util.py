from typing import List

import numpy as np
import openai
import tiktoken
from flask_login import current_user
from openai import RateLimitError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, wait_random_exponential

from app import db
from app.models.chat_models import ChatPreferences
from app.models.embedding_models import DocumentChunk, Document, ModelContextWindow
from app.utils.vector_cache import VectorCache


def num_tokens(text: str, model: str = "gpt-4-turbo-preview") -> int:
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))


def find_relevant_sections(user_id, query_embedding, user_preferences):
    context_window_size = 60000

    max_sections = user_preferences.knowledge_context_tokens
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

    # Select chunks based on the max number of sections and token limit
    selected_chunks = []
    sections_appended = 0
    current_tokens = 0

    for chunk_id, similarity in similarities:
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


@retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(6))
def get_embedding(text: str, client: openai.OpenAI, model="text-embedding-3-large", **kwargs) -> List[float]:
    response = client.embeddings.create(input=text, model=model, **kwargs)
    embedding = response.data[0].embedding
    if len(embedding) != 3072:
        raise ValueError(f"Expected embedding dimension to be 3072, but got {len(embedding)}")
    return embedding


def append_knowledge_context(user_query, user_id, client):
    query_embedding = get_embedding(user_query, client)
    query_vector = np.array(query_embedding, dtype=np.float32)
    user_preferences = user_preferences = db.session.query(ChatPreferences).filter_by(user_id=user_id).one()

    relevant_sections = find_relevant_sections(user_id, query_vector, user_preferences=user_preferences)
    context = ""
    chunk_associations = []
    doc_pages = {}  # Dictionary to hold document ID and a set of pages

    preface = "Use the below textual excerpts to answer the subsequent question. If the answer cannot be found in the provided text, say as such but still do your best to provide the most factual, nuanced assessment possible."

    context = preface
    chunk_associations = []
    for chunk_id, title, author, pages, chunk_content, tokens, similarity in relevant_sections:
        context_parts = []
        if title:
            context_parts.append(f"Title: {title}")
        if author:
            context_parts.append(f"Author: {author}")
        if title not in doc_pages:
            doc_pages[title] = set()
        if pages:  # Add page number only if it exists
            context_parts.append(f"Page: {pages}")
            doc_pages[title].add(pages)
        context_parts.append(f"Content:\n{chunk_content}")

        context += "\n".join(context_parts) + "\n\n"

        chunk_associations.append((chunk_id, similarity))

    modified_query = context + user_query
    return modified_query, chunk_associations, doc_pages


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(RateLimitError),
)
def chat_completion_with_retry(messages, model, client, temperature):
    return client.chat.completions.create(model=model, messages=messages, temperature=temperature, stream=True)


def ask(query, client, model: str = "gpt-4-turbo-preview"):
    modified_query, chunk_associations, doc_pages = append_knowledge_context(query, current_user.id, client)
    messages = [
        {
            "role": "system",
            "content": "You are a helpful academic literary assistant. Provide in-depth guidance, suggestions, code snippets, and explanations as needed to help the user. Leverage your expertise and intuition to offer innovative and effective solutions. Be informative, clear, and concise in your responses, and focus on providing accurate and reliable information. Use the provided text excerpts directly to aid in your responses.",
        },
        {"role": "user", "content": modified_query},
    ]
    preferences = ChatPreferences.query.filter_by(user_id=current_user.id).first()
    temperature = preferences.temperature
    try:
        documents_used_summary = "\nDocuments used:\n"
        for title, pages in doc_pages.items():
            if pages:
                documents_used_summary += f"{title}: Pages {', '.join(map(str, sorted(pages)))}, "
            else:  # Handle documents without pages
                documents_used_summary += f"{title}, "
        yield documents_used_summary + "\n\n"

        # Yield the AI response parts
        for part in chat_completion_with_retry(messages, model, client, temperature):
            content = part.choices[0].delta.content
            if content:
                yield content
    except RateLimitError as e:
        print(f"Rate limit exceeded. All retry attempts failed.")
    except openai.OpenAIError as e:
        print(f"An OpenAI error occurred: {e}")
