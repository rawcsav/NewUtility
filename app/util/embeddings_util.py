import os
import pickle
import re
import tempfile
import unicodedata
from typing import List

import numpy as np
import openai
import tiktoken
from docx2txt import docx2txt
from flask_login import current_user
from nltk.tokenize import word_tokenize, sent_tokenize
from pypdf import PdfReader
from tenacity import retry, stop_after_attempt, wait_random_exponential
from werkzeug.utils import secure_filename

from app import db
from app.database import (
    DocumentChunk,
    DocumentEmbedding,
    ChatPreferences,
    ModelContextWindow,
    Document,
)
from app.util.vector_cache import VectorCache

ENCODING = tiktoken.get_encoding("cl100k_base")
EMBEDDING_MODEL = "text-embedding-ada-002"
MAX_TOKENS_PER_BATCH = 8000  # Define the maximum tokens per batch
WORDS_PER_PAGE = 500  # Define the number of words per page


def save_temp_file(uploaded_file):
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, secure_filename(uploaded_file.filename))
    uploaded_file.save(temp_path)
    return temp_path


def remove_temp_file(temp_path):
    temp_dir = os.path.dirname(temp_path)
    os.remove(temp_path)
    os.rmdir(temp_dir)


def count_tokens(string: str) -> int:
    num_tokens = len(ENCODING.encode(string))
    return num_tokens


def extract_text_from_pdf(filepath):
    page_texts = []
    with open(filepath, "rb") as file:
        reader = PdfReader(file)
        for page_number, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text()
            if page_text:
                page_texts.append((page_text, page_number))
    return page_texts


def estimate_pages(text):
    words = word_tokenize(text)
    pages = [
        (text[i : i + WORDS_PER_PAGE], i // WORDS_PER_PAGE + 1)
        for i in range(0, len(words), WORDS_PER_PAGE)
    ]
    return pages


def extract_text_from_file(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".pdf":
        return extract_text_from_pdf(filepath)
    elif ext in [".docx", ".txt"]:
        if ext == ".docx":
            text = docx2txt.process(filepath)
        else:  # ext == ".txt"
            with open(filepath, "r", encoding="utf-8") as file:
                text = file.read()
        # Estimate page numbers based on word count
        return estimate_pages(text)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def preprocess_text(text):
    # Remove copyright notices
    text = re.sub(r"©.*?\n", "", text)
    # Replace newlines with space
    text = re.sub(r"\n", " ", text)
    # Replace multiple spaces with a single space
    text = re.sub(r"\s+", " ", text)
    # Remove URLs
    text = re.sub(r"https?://\S+|www\.\S+", "", text)
    # Remove email addresses
    text = re.sub(r"\S*@\S*\s?", "", text)
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Remove or replace words with accents
    text = "".join(
        (
            c
            for c in unicodedata.normalize("NFD", text)
            if unicodedata.category(c) != "Mn"
        )
    )
    # Remove punctuation
    text = re.sub(r"[^\w\s.?!]", "", text)

    return text.strip().lower()


def split_text(text_pages, max_tokens=512):
    # text_pages is a list of tuples (text, page_number)
    chunks = []
    chunk_pages = []  # List to hold the pages for each chunk
    current_chunk = []
    current_chunk_token_count = 0
    current_chunk_pages = set()  # Keep track of pages in the current chunk

    for text, page_number in text_pages:
        text = preprocess_text(text)
        sentences = sent_tokenize(text)

        for sentence in sentences:
            sentence_token_count = count_tokens(sentence)
            if sentence_token_count > max_tokens:
                words = word_tokenize(sentence)
                current_sentence_chunk = []
                for word in words:
                    word_token_count = count_tokens(word)
                    if current_chunk_token_count + word_token_count <= max_tokens:
                        current_sentence_chunk.append(word)
                        current_chunk_token_count += word_token_count
                    else:
                        # When the current chunk is full, save it and start a new one
                        chunks.append(" ".join(current_sentence_chunk))
                        chunk_pages.append(current_chunk_pages.copy())
                        current_sentence_chunk = [word]
                        current_chunk_token_count = word_token_count
                        current_chunk_pages = set([page_number])
                if current_sentence_chunk:
                    # Add the remaining words from the long sentence as a new chunk
                    chunks.append(" ".join(current_sentence_chunk))
                    chunk_pages.append(current_chunk_pages.copy())
                # Reset for a new sentence
                current_chunk = []
                current_chunk_token_count = 0
                current_chunk_pages = set([page_number])
            elif current_chunk_token_count + sentence_token_count <= max_tokens:
                current_chunk.append(sentence)
                current_chunk_token_count += sentence_token_count
                current_chunk_pages.add(page_number)
            else:
                # If the current chunk is full, start a new chunk
                chunks.append(" ".join(current_chunk))
                chunk_pages.append(current_chunk_pages.copy())
                current_chunk = [sentence]
                current_chunk_token_count = sentence_token_count
                current_chunk_pages = set([page_number])

    # Add the last chunk if it's not empty
    if current_chunk:
        chunks.append(" ".join(current_chunk))
        chunk_pages.append(current_chunk_pages)

    # Calculate the token count for each chunk
    chunk_token_counts = [count_tokens(chunk) for chunk in chunks]
    total_tokens = sum(chunk_token_counts)
    return chunks, chunk_pages, total_tokens, chunk_token_counts


@retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(6))
def get_embedding(
    text: str, client: openai.OpenAI, model=EMBEDDING_MODEL, **kwargs
) -> List[float]:
    response = client.embeddings.create(input=text, model=model, **kwargs)

    return response.data[0].embedding


def get_embedding_batch(
    texts: List[str], client: openai.OpenAI, model=EMBEDDING_MODEL, **kwargs
) -> List[List[float]]:
    embeddings = []
    current_batch = []
    current_tokens = 0

    for text in texts:
        text = text.replace("\n", " ")
        token_estimate = count_tokens(text)
        if current_tokens + token_estimate > MAX_TOKENS_PER_BATCH:
            batch_embeddings = [
                get_embedding(single_text, client, model, **kwargs)
                for single_text in current_batch
            ]
            embeddings.extend(batch_embeddings)
            current_batch = []
            current_tokens = 0

        current_batch.append(text)
        current_tokens += token_estimate

    if current_batch:
        batch_embeddings = [
            get_embedding(single_text, client, model, **kwargs)
            for single_text in current_batch
        ]
        embeddings.extend(batch_embeddings)

    return embeddings


def serialize_embedding(embedding_list):
    return pickle.dumps(embedding_list)





def store_embeddings(document_id, embeddings):
    chunks = DocumentChunk.query.filter_by(document_id=document_id).all()
    if len(chunks) != len(embeddings):
        raise ValueError(
            "The number of embeddings does not match the number of document chunks."
        )

    for chunk, embedding_vector in zip(chunks, embeddings):
        embedding_model = DocumentEmbedding(
            chunk_id=chunk.id,
            embedding=serialize_embedding(embedding_vector),
            user_id=current_user.id,
            model=EMBEDDING_MODEL,
        )
        db.session.add(embedding_model)
        db.session.commit()
        VectorCache.load_user_vectors(current_user.id)

def cosine_similarity(vec_a, vec_b):
    return np.dot(vec_a, vec_b)


def get_associated_text(id):
    embedding = DocumentEmbedding.query.filter_by(chunk_id=id).first()
    if embedding:
        chunk = DocumentChunk.query.filter_by(id=embedding.chunk_id).first()
        return chunk.content if chunk else None
    return None


def find_relevant_sections(user_id, query_embedding, user_preferences):
    context_window_size = (
        db.session.query(ModelContextWindow.context_window_size)
        .filter_by(model_name=user_preferences.model)
        .scalar()
    )
    max_knowledge_context_tokens = (
        user_preferences.knowledge_context_tokens / 100.0
    ) * context_window_size

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

    # Select chunks that fit within the max_knowledge_context_tokens limit
    selected_chunks = []
    current_tokens = 0
    for chunk_id, similarity in similarities:
        chunk = next((c for c in document_chunks_with_details if str(c.id) == chunk_id), None)
        if chunk and current_tokens + chunk.tokens <= max_knowledge_context_tokens:
            selected_chunks.append(
                (
                    chunk.id,
                    chunk.title,
                    chunk.author,
                    chunk.pages,
                    chunk.content,
                    chunk.tokens,
                    similarity,
                )
            )
            current_tokens += chunk.tokens
        else:
            break

    return selected_chunks


def append_knowledge_context(user_query, user_id, client):
    # Fetch user's chat preferences
    user_preferences = (
        db.session.query(ChatPreferences).filter_by(user_id=user_id).one()
    )

    # Check if knowledge retrieval is enabled
    if not user_preferences.knowledge_query_mode:
        return user_query

    # Embed the user query
    query_embedding = get_embedding(user_query, client)

    # Find relevant sections
    relevant_sections = find_relevant_sections(
        user_id, query_embedding, user_preferences
    )  # Ensure find_relevant_sections is implemented

    # Format the context with title, author, and page number
    context = ""
    chunk_associations = []
    for (
        chunk_id,
        title,
        author,
        pages,
        chunk_content,
        similarity,
        rank,
    ) in relevant_sections:
        context_parts = []
        if title:
            context_parts.append(f"Title: {title}")
        if author:
            context_parts.append(f"Author: {author}")
        if pages:
            context_parts.append(f"Page: {pages}")
        context_parts.append(f"Content: {chunk_content}")  # Include the chunk content

        context += "\n".join(context_parts) + "\n\n"

        chunk_associations.append((chunk_id, rank))

    modified_query = context + user_query
    return modified_query, chunk_associations
