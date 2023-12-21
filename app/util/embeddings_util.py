import pickle
import re
import zlib
from typing import List
import unicodedata

from flask_login import current_user
from tenacity import retry, stop_after_attempt, wait_random_exponential
import openai
from PyPDF2 import PdfReader
from docx2txt import docx2txt
from nltk.tokenize import word_tokenize, sent_tokenize
import tiktoken
from app import db
from app.database import DocumentChunk, DocumentEmbedding
import os
from werkzeug.utils import secure_filename
import tempfile

ENCODING = tiktoken.get_encoding("cl100k_base")
EMBEDDING_MODEL = 'text-embedding-ada-002'
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
    pages = [(text[i:i + WORDS_PER_PAGE], i // WORDS_PER_PAGE + 1) for i in
             range(0, len(words), WORDS_PER_PAGE)]
    return pages


def extract_text_from_file(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".pdf":
        return extract_text_from_pdf(filepath)
    elif ext in [".docx", ".txt"]:
        if ext == ".docx":
            text = docx2txt.process(filepath)
        else:  # ext == ".txt"
            with open(filepath, 'r', encoding='utf-8') as file:
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
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    # Remove email addresses
    text = re.sub(r'\S*@\S*\s?', '', text)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove or replace words with accents
    text = ''.join((c for c in unicodedata.normalize('NFD', text) if
                    unicodedata.category(c) != 'Mn'))
    # Remove punctuation
    text = re.sub(r'[^\w\s.?!]', '', text)

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
                # Split the sentence into words and create chunks that fit within max_tokens
                words = word_tokenize(sentence)
                current_sentence_chunk = []
                for word in words:
                    word_token_count = count_tokens(word)
                    if current_chunk_token_count + word_token_count <= max_tokens:
                        current_sentence_chunk.append(word)
                        current_chunk_token_count += word_token_count
                    else:
                        # When the current chunk is full, save it and start a new one
                        chunks.append(' '.join(current_sentence_chunk))
                        chunk_pages.append(current_chunk_pages.copy())
                        current_sentence_chunk = [word]
                        current_chunk_token_count = word_token_count
                        current_chunk_pages = set([page_number])
                if current_sentence_chunk:
                    # Add the remaining words from the long sentence as a new chunk
                    chunks.append(' '.join(current_sentence_chunk))
                    chunk_pages.append(current_chunk_pages.copy())
                # Reset for a new sentence
                current_chunk = []
                current_chunk_token_count = 0
                current_chunk_pages = set([page_number])
            elif current_chunk_token_count + sentence_token_count <= max_tokens:
                # If the current chunk plus the new sentence is less than max_tokens, add it
                current_chunk.append(sentence)
                current_chunk_token_count += sentence_token_count
                current_chunk_pages.add(page_number)
            else:
                # If the current chunk is full, start a new chunk
                chunks.append(' '.join(current_chunk))
                chunk_pages.append(current_chunk_pages.copy())
                current_chunk = [sentence]
                current_chunk_token_count = sentence_token_count
                current_chunk_pages = set([page_number])

    # Add the last chunk if it's not empty
    if current_chunk:
        chunks.append(' '.join(current_chunk))
        chunk_pages.append(current_chunk_pages)

    # Calculate the token count for each chunk
    chunk_token_counts = [count_tokens(chunk) for chunk in chunks]
    total_tokens = sum(chunk_token_counts)

    return chunks, chunk_pages, total_tokens, chunk_token_counts


@retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(6))
def get_embedding(text: str, client: openai.OpenAI, model=EMBEDDING_MODEL,
                  **kwargs) -> \
        List[
            float]:
    response = client.embeddings.create(input=text, model=model, **kwargs)

    return response.data[0].embedding


def get_embedding_batch(texts: List[str], client: openai.OpenAI, model=EMBEDDING_MODEL,
                        **kwargs) -> List[List[float]]:
    embeddings = []
    current_batch = []
    current_tokens = 0

    for text in texts:
        text = text.replace("\n", " ")
        token_estimate = count_tokens(text)
        if current_tokens + token_estimate > MAX_TOKENS_PER_BATCH:
            # Process the current batch
            batch_embeddings = [get_embedding(single_text, client, model, **kwargs) for
                                single_text in current_batch]
            embeddings.extend(batch_embeddings)
            # Reset for next batch
            current_batch = []
            current_tokens = 0

        current_batch.append(text)
        current_tokens += token_estimate

    # Process any remaining texts in the final batch
    if current_batch:
        batch_embeddings = [get_embedding(single_text, client, model, **kwargs) for
                            single_text in current_batch]
        embeddings.extend(batch_embeddings)

    return embeddings


def serialize_embedding(embedding_list):
    return pickle.dumps(embedding_list)


def deserialize_embedding(serialized_embedding):
    return pickle.loads(serialized_embedding)


def compress_embedding(serialized_embedding):
    return zlib.compress(serialized_embedding)


def decompress_embedding(compressed_embedding):
    return zlib.decompress(compressed_embedding)


def prepare_embedding_for_storage(embedding):
    serialized_embedding = serialize_embedding(embedding)
    compressed_embedding = compress_embedding(serialized_embedding)
    return compressed_embedding


def retrieve_embedding_from_storage(compressed_embedding):
    serialized_embedding = decompress_embedding(compressed_embedding)
    embedding = deserialize_embedding(serialized_embedding)
    return embedding.tolist()  # Convert back to a list, if that's the preferred format


def store_embeddings(document_id, embeddings):
    chunks = DocumentChunk.query.filter_by(document_id=document_id).all()
    if len(chunks) != len(embeddings):
        raise ValueError(
            "The number of embeddings does not match the number of document chunks.")

    for chunk, embedding_vector in zip(chunks, embeddings):
        embedding_model = DocumentEmbedding(
            chunk_id=chunk.id,
            embedding=serialize_embedding(embedding_vector),
            user_id=current_user.id,
            model=EMBEDDING_MODEL
        )
        db.session.add(embedding_model)
