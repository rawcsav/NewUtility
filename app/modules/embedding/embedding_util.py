import os
import re
import unicodedata
import uuid
from typing import List, Tuple, Set

from nltk.data import find
from flask_login import current_user

from app.modules.user.user_util import get_user_upload_directory
import numpy as np
import openai
import tiktoken
from docx2txt import docx2txt
from nltk.tokenize import word_tokenize, sent_tokenize
from pypdf import PdfReader
from werkzeug.utils import secure_filename

from app import db
from app.models.embedding_models import ModelContextWindow, Document, DocumentChunk, DocumentEmbedding
from app.models.chat_models import ChatPreferences
from app.utils.vector_cache import VectorCache

ENCODING = tiktoken.get_encoding("cl100k_base")
EMBEDDING_MODEL = "text-embedding-3-large"
MAX_TOKENS_PER_BATCH = 8000  # Define the maximum tokens per batch
WORDS_PER_PAGE = 500  # Define the number of words per page


def download_nltk_data():
    try:
        # Check if punkt tokenizer data is available
        find("tokenizers/punkt")
    except LookupError:
        import nltk

        print("Downloading NLTK 'punkt' tokenizer data...")
        nltk.download("punkt")
        print("'punkt' tokenizer data downloaded.")


def extract_uuid_from_path(temp_path):
    file_name = os.path.basename(temp_path)
    match = re.match(r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})", file_name)
    if match:
        return match.group(1)
    else:
        raise ValueError("UUID not found in temp_path")

def save_temp(uploaded_file):
    temp_dir = get_user_upload_directory(current_user.id)
    file_extension = os.path.splitext(uploaded_file.filename)[1]
    uuid_filename = f"{uuid.uuid4()}{file_extension}"
    temp_path = os.path.join(temp_dir, secure_filename(uuid_filename))
    uploaded_file.save(temp_path)
    return temp_path


def count_tokens(string: str) -> int:
    num_tokens = len(ENCODING.encode(string))
    return num_tokens

def preprocess_text(text):
    text = re.sub(r"©.*?\n", "", text)
    text = re.sub(r"\n", " ", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"https?://\S+|www\.\S+", "", text)
    text = re.sub(r"\S*@\S*\s?", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = "".join((c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"))
    text = re.sub(r"[^\w\s.?!]", "", text)

    return text.strip().lower()

def get_embedding(text: str, client: openai.OpenAI, model=EMBEDDING_MODEL, **kwargs) -> List[float]:
    response = client.embeddings.create(input=text, model=model, **kwargs)
    embedding = response.data[0].embedding
    print(embedding[:10])
    if len(embedding) != 3072:
        raise ValueError(f"Expected embedding dimension to be 3072, but got {len(embedding)}")
    return embedding


def get_embedding_batch(texts: List[str], client: openai.OpenAI, model=EMBEDDING_MODEL, **kwargs) -> List[List[float]]:
    embeddings = []
    current_batch = []
    current_tokens = 0

    for text in texts:
        text = text.replace("\n", " ")
        token_estimate = count_tokens(text)
        if current_tokens + token_estimate > MAX_TOKENS_PER_BATCH:
            batch_embeddings = [get_embedding(single_text, client, model, **kwargs) for single_text in current_batch]
            embeddings.extend(batch_embeddings)
            current_batch = []
            current_tokens = 0

        current_batch.append(text)
        current_tokens += token_estimate

    if current_batch:
        batch_embeddings = [get_embedding(single_text, client, model, **kwargs) for single_text in current_batch]
        embeddings.extend(batch_embeddings)

        for batch_embedding in batch_embeddings:
            if len(batch_embedding) != 3072:
                raise ValueError(f"Expected embedding dimension to be 3072, but got {len(batch_embedding)}")

    return embeddings


def store_embeddings(session, document_id, embeddings, user_id):
    chunks = session.query(DocumentChunk).filter_by(document_id=document_id).all()
    if len(chunks) != len(embeddings):
        raise ValueError("The number of embeddings does not match the number of document chunks.")

    embedding_models = []
    for chunk, embedding_vector in zip(chunks, embeddings):
        embedding_bytes = np.array(embedding_vector, dtype=np.float32).tobytes()
        embedding_model = DocumentEmbedding(
            chunk_id=chunk.id, embedding=embedding_bytes, user_id=user_id, model=EMBEDDING_MODEL  # Store as binary data
        )
        embedding_models.append(embedding_model)

    session.bulk_save_objects(embedding_models)
    session.commit()



def find_relevant_sections(user_id, query_embedding, user_preferences):
    # Fetch the context window size
    context_window_size = (
        db.session.query(ModelContextWindow.context_window_size).filter_by(model_name=user_preferences.model).scalar()
    )

    # max_knowledge_context_tokens is now the maximum number of sections
    max_sections = user_preferences.knowledge_context_tokens

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


def append_knowledge_context(user_query, user_id, client):
    user_preferences = db.session.query(ChatPreferences).filter_by(user_id=user_id).one()
    if not user_preferences.knowledge_query_mode:
        return user_query

    # Embed the user query
    query_embedding = get_embedding(user_query, client)
    query_vector = np.array(query_embedding, dtype=np.float32)

    # Find relevant sections
    relevant_sections = find_relevant_sections(user_id, query_vector, user_preferences)
    context = ""
    chunk_associations = []

    preface = "Use the below textual excerpts to answer the subsequent question. If the answer cannot be found in the provided text, say as such but still do your best to provide the most factual, nuanced assessment possible.\n\n"

    # Format the context with title, author, and page number
    context = preface
    chunk_associations = []
    for chunk_id, title, author, pages, chunk_content, tokens, similarity in relevant_sections:
        context_parts = []
        if title:
            context_parts.append(f"Title: {title}")
        if author:
            context_parts.append(f"Author: {author}")
        if pages:
            context_parts.append(f"Page: {pages}")
        context_parts.append(f"Content:\n{chunk_content}")  # Include the chunk content

        context += "\n".join(context_parts) + "\n\n"

        chunk_associations.append((chunk_id, similarity))
    modified_query = context + user_query
    return modified_query, chunk_associations


def delete_all_documents():
    try:
        # Query all documents
        all_documents = Document.query.all()

        # Delete each document
        for document in all_documents:
            db.session.delete(document)

        # Commit the transaction
        db.session.commit()
    except Exception as e:
        db.session.rollback()

class TextExtractor:
    def __init__(self, filepath):
        self.filepath = filepath
        self.last_page_number = None

    def extract_text_from_pdf(self):
        with open(self.filepath, "rb") as file:
            reader = PdfReader(file)
            for page_number, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text()
                if page_text:
                    yield (page_text, page_number)
            self.last_page_number = page_number

    def extract_text_from_file(self):
        ext = os.path.splitext(self.filepath)[1].lower()
        if ext == ".pdf":
            yield from self.extract_text_from_pdf()
        elif ext == ".docx":
            text = docx2txt.process(self.filepath)
            yield (text, None)  # Assuming docx doesn't provide page numbers
            self.last_page_number = None  # Reset or handle as needed for DOCX
        elif ext == ".txt":
            with open(self.filepath, "r", encoding="utf-8") as file:
                for line_number, line in enumerate(file, start=1):
                    yield (line.strip(), None)
            self.last_page_number = line_number
        else:
            raise ValueError(f"Unsupported file type: {ext}")

    def get_final_page_amount(self):
        return self.last_page_number

class TextSplitter:
    def __init__(self, max_tokens: int = 512):
        self.max_tokens = max_tokens
        self.chunks = []
        self.chunk_pages = []
        self.current_chunk = []
        self.current_chunk_token_count = 0
        self.current_chunk_pages = set()
        download_nltk_data()

    def add_text(self, text: str, page_number: int = None):
        text = preprocess_text(text)
        sentences = sent_tokenize(text)

        for sentence in sentences:
            sentence_token_count = count_tokens(sentence)
            if sentence_token_count > self.max_tokens:
                words = word_tokenize(sentence)
                self._process_long_sentence(words, page_number)
            elif self.current_chunk_token_count + sentence_token_count <= self.max_tokens:
                self._add_sentence_to_current_chunk(sentence, page_number)
            else:
                self._finalize_current_chunk(page_number)
                self._add_sentence_to_current_chunk(sentence, page_number)

    def _process_long_sentence(self, words: List[str], page_number: int):
        current_sentence_chunk = []
        for word in words:
            word_token_count = count_tokens(word)
            if self.current_chunk_token_count + word_token_count <= self.max_tokens:
                current_sentence_chunk.append(word)
                self.current_chunk_token_count += word_token_count
            else:
                self.chunks.append(" ".join(current_sentence_chunk))
                self.chunk_pages.append(self.current_chunk_pages.copy() if page_number is not None else None)
                current_sentence_chunk = [word]
                self.current_chunk_token_count = word_token_count
                self.current_chunk_pages = {page_number} if page_number is not None else set()
        if current_sentence_chunk:
            self.chunks.append(" ".join(current_sentence_chunk))
            self.chunk_pages.append(self.current_chunk_pages.copy() if page_number is not None else None)
        self.current_chunk = []
        self.current_chunk_token_count = 0
        self.current_chunk_pages = {page_number} if page_number is not None else set()

    def _add_sentence_to_current_chunk(self, sentence: str, page_number: int):
        self.current_chunk.append(sentence)
        self.current_chunk_token_count += count_tokens(sentence)
        if page_number is not None:
            self.current_chunk_pages.add(page_number)

    def _finalize_current_chunk(self, page_number: int = None):
        if self.current_chunk:
            self.chunks.append(" ".join(self.current_chunk))
            self.chunk_pages.append(self.current_chunk_pages.copy() if page_number is not None else None)
        self.current_chunk = []
        self.current_chunk_token_count = 0
        self.current_chunk_pages = set()

    def finalize(self) -> Tuple[List[str], List[Set[int]], int, List[int]]:
        self._finalize_current_chunk()
        chunk_token_counts = [count_tokens(chunk) for chunk in self.chunks]
        total_tokens = sum(chunk_token_counts)
        return self.chunks, self.chunk_pages, total_tokens, chunk_token_counts