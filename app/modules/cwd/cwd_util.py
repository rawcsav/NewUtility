from typing import List

import numpy as np
import openai
import tiktoken
from flask_login import current_user
from openai import RateLimitError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, wait_random_exponential

from app import db
from app.models.embedding_models import DocumentChunk, Document
from app.utils.vector_cache import VectorCache


def num_tokens(text: str, model: str = "gpt-4-turbo-preview") -> int:
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))


def find_relevant_sections(user_id, query_embedding):
    # max_knowledge_context_tokens is now the maximum number of sections
    max_sections = 20

    # Fetch the document chunks and additional details for the user
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
            # Stop if the maximum number of sections has been reached
            break

        chunk = next((c for c in document_chunks_with_details if str(c.id) == chunk_id), None)
        if chunk and current_tokens + chunk.tokens <= 60000:
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

    # Find relevant sections
    relevant_sections = find_relevant_sections(user_id, query_vector)
    context = ""
    chunk_associations = []

    preface = "Use the below textual excerpts to answer the subsequent question. If the answer cannot be found in the provided text, say as such but still do your best to provide the most factual, nuanced assessment possible."

    context = preface
    chunk_associations = []
    for chunk_id, title, author, pages, chunk_content, tokens, similarity in relevant_sections:
        context_parts = []
        if title:
            context_parts.append(f"Title: {title}")
        if pages:
            context_parts.append(f"Page: {pages}")
        context_parts.append(f"Content:\n{chunk_content}")  # Include the chunk content

        context += "\n".join(context_parts) + "\n\n"

        chunk_associations.append((chunk_id, similarity))
    modified_query = context + user_query
    return modified_query, chunk_associations


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(RateLimitError),
)
def chat_completion_with_retry(messages, model, client):
    return client.chat.completions.create(model=model, messages=messages, temperature=0.6, stream=True)


def ask(query, client, model: str = "gpt-4-turbo-preview"):
    modified_query, chunk_associations = append_knowledge_context(query, current_user.id, client)
    messages = [
        {
            "role": "system",
            "content": "You are a helpful academic literary assistant. Provide in-depth guidance, suggestions, code snippets, and explanations as needed to help the user. Leverage your expertise and intuition to offer innovative and effective solutions. Be informative, clear, and concise in your responses, and focus on providing accurate and reliable information. Use the provided text excerpts directly to aid in your responses.",
        },
        {"role": "user", "content": modified_query},
    ]
    try:
        for part in chat_completion_with_retry(messages, model, client):
            content = part.choices[0].delta.content
            if content:
                yield content
    except RateLimitError as e:
        print(f"Rate limit exceeded. All retry attempts failed.")
    except openai.OpenAIError as e:
        print(f"An OpenAI error occurred: {e}")
    yield "\n\nDocuments used:\n"
    for title, pages in chunk_associations:
        yield f"Title: {title}\n\nPage: {pages}\n"
