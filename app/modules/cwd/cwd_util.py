import concurrent.futures
import os
import re
import shutil
import time
from datetime import datetime, timedelta
from typing import Dict, Tuple, List, Any

import docx2txt
import openai
import pandas as pd
import tiktoken
from flask import current_app
from flask_login import current_user
from pypdf import PdfReader
from nltk.tokenize import word_tokenize, sent_tokenize
from openai import RateLimitError
from scipy import spatial
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, wait_random_exponential


def get_first_10_words(text):
    words = word_tokenize(text)
    return " ".join(words[:10])


def num_tokens(text: str, model: str = "gpt-4-turbo-preview") -> int:
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))


def preprocess_text(text):
    # Remove copyright and source information
    text = re.sub(r"©.*?\n", "", text)

    # Remove download instructions
    text = re.sub(r"Download : Download full-size image", "", text)

    # Replace newline characters with space
    text = re.sub(r"\n", " ", text)

    # Replace multiple spaces with a single space
    text = re.sub(r"\s+", " ", text)

    return text


def split_text(text, document_title):
    text = preprocess_text(text)
    sentences = sent_tokenize(text)

    sections = []
    current_section = {"title": document_title, "loc": "", "text": "", "tokens": 0}
    current_sentences = []

    for sentence in sentences:
        tokens_count = num_tokens(sentence)

        if current_section["tokens"] + tokens_count > 1000:
            current_section["text"] = " ".join(current_sentences)
            current_section["loc"] = get_first_10_words(current_section["text"])
            sections.append(current_section)
            current_sentences = [sentence]
            current_section = {"title": document_title, "loc": "", "text": "", "tokens": tokens_count}
        else:
            current_sentences.append(sentence)
            current_section["tokens"] += tokens_count

    if current_sentences:
        current_section["text"] = " ".join(current_sentences)
        current_section["loc"] = get_first_10_words(current_section["text"])
        sections.append(current_section)

    return sections


def extract_text_from_file(filepath):
    ext = os.path.splitext(filepath)[1].lower()

    # If the file is already a .txt, return its path
    if ext == ".txt":
        return filepath

    extracted_text = ""

    try:
        if ext == ".pdf":
            with open(filepath, "rb") as file:
                reader = PdfReader(file)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:  # ensure there's text on the page
                        extracted_text += page_text

        elif ext == ".docx":
            extracted_text = docx2txt.process(filepath)

        else:
            raise ValueError("Unsupported file type: {}".format(ext))

        # Create a .txt version of the extracted text
        txt_filepath = os.path.splitext(filepath)[0] + ".txt"
        with open(txt_filepath, "w", encoding="utf-8") as txt_file:
            txt_file.write(extracted_text)

        # Delete the original file after creating the .txt version
        os.remove(filepath)

        return txt_filepath
    except Exception as e:
        print(f"Error processing the file {filepath}. Details: {e}")


def gather_text_sections(folder_path):
    dfs = []

    for filename in os.listdir(folder_path):
        # Only consider .txt files
        if filename.endswith(".txt"):
            filepath = os.path.join(folder_path, filename)

            with open(filepath, "r", encoding="utf-8") as file:
                extracted_text = file.read()

            original_title = os.path.splitext(filename)[0]
            sections = split_text(
                extracted_text, original_title
            )  # Assuming split_text is defined elsewhere in your code
            df = pd.DataFrame(sections)
            dfs.append(df)

    return pd.concat(dfs, ignore_index=True)


@retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(6))
def get_embedding(text: str, client: openai.OpenAI, **kwargs) -> List[float]:
    response = client.embeddings.create(input=text, model="text-embedding-3-large", **kwargs)
    embedding = response.data[0].embedding
    if len(embedding) != 3072:
        raise ValueError(f"Expected embedding dimension to be 3072, but got {len(embedding)}")
    return embedding


def compute_doc_embeddings(df: pd.DataFrame, client, batch_size=2, num_workers=6) -> Dict[Tuple[str, str], List[float]]:
    embeddings = {}

    def process_batch(batch: pd.DataFrame) -> Dict[Tuple[str, str], List[float]]:
        batch_embeddings = {}
        texts = [r.text for idx, r in batch.iterrows()]
        for j, text in enumerate(texts):
            embedding = get_embedding(text, client)
            if embedding is None:
                print("Failed to compute embedding for document with index:", batch.index[j])
            else:
                batch_embeddings[batch.index[j]] = embedding
        return batch_embeddings

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = []
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i : i + batch_size]
            futures.append(executor.submit(process_batch, batch))

        for future in concurrent.futures.as_completed(futures):
            embeddings.update(future.result())

    return embeddings


def add_embeddings_to_df(df, client):
    document_embeddings = compute_doc_embeddings(df, client)

    df["embeddings"] = document_embeddings
    return df


def strings_ranked_by_relatedness(
    query: str, df: pd.DataFrame, client, relatedness_fn=lambda x, y: 1 - spatial.distance.cosine(x, y), top_n: int = 20
) -> pd.DataFrame:
    response = client.embeddings.create(input=query, model="text-embedding-3-large")
    query_embedding = response.data[0].embedding

    df["relatedness"] = df["embeddings"].apply(lambda x: relatedness_fn(query_embedding, x))
    sorted_df = df.sort_values(by="relatedness", ascending=False).head(top_n)
    return sorted_df


def process_filenames(filenames: List[str]) -> List[str]:
    return [filename.replace(".txt", "") for filename in filenames]


def query_message(query: str, df: pd.DataFrame, client, model: str, token_budget: int, specific_documents=None) -> str:
    df["title"] = df["title"].astype(str)
    if specific_documents:
        specific_documents = process_filenames(specific_documents)
        df_filtered = df[df["title"].isin(specific_documents)]
    else:
        df_filtered = df

    sorted_df = strings_ranked_by_relatedness(query, df_filtered, client)
    introduction = "Use the below textual excerpts to answer the subsequent question. If the answer cannot be found in the provided text, say as such but still do your best to provide the most factual, nuanced assessment possible."
    question = f"\n\nQuestion: {query}"

    message = introduction
    full_message = introduction

    docs_used = []
    for _, row in sorted_df.iterrows():
        doc_info = f'\n\nTitle: {row["title"]}'
        next_article = doc_info + f'\nTextual excerpt section:\n"""\n{row["text"]}\n"""'
        if num_tokens(full_message + next_article + question, model=model) <= token_budget:
            message += doc_info
            full_message += next_article
            docs_used.append(row["title"])
            docs_used = list(set(docs_used))
    full_message += question
    return message, full_message, docs_used


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(RateLimitError),
)
def chat_completion_with_retry(messages, model, client):
    return client.chat.completions.create(model=model, messages=messages, temperature=0.6, stream=True)


def ask(query: str, df: pd.DataFrame, client, model: str = "gpt-4-turbo-preview", specific_documents=None):
    prompt = query
    token_budget = 60000 - num_tokens(prompt, model=model)

    message, full_message, docs_used = query_message(
        prompt, df, client, model=model, token_budget=token_budget, specific_documents=specific_documents
    )

    messages = [
        {
            "role": "system",
            "content": "You are a helpful academic literary assistant. Provide in-depth guidance, suggestions, code snippets, and explanations as needed to help the user. Leverage your expertise and intuition to offer innovative and effective solutions. Be informative, clear, and concise in your responses, and focus on providing accurate and reliable information. Use the provided text excerpts directly to aid in your responses.",
        },
        {"role": "user", "content": full_message},
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
    for title in docs_used:
        yield f"Title: {title}\n"


def allowed_file(filename):
    ALLOWED_EXTENSIONS = {"txt", "pdf", "docx"}
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def remove_directory(directory_path):
    if not os.path.exists(directory_path):
        print(f"The directory {directory_path} does not exist.")
        return
    shutil.rmtree(directory_path)
    print(f"The directory {directory_path} has been removed.")


class FileNotFoundError(Exception):
    pass


def is_stale(path, threshold_minutes=180):
    mtime = datetime.fromtimestamp(os.path.getmtime(path))
    return datetime.utcnow() - mtime > timedelta(minutes=threshold_minutes)


def cleanup_path(path, threshold_minutes=180):
    for root, dirs, files in os.walk(path, topdown=False):  # `topdown=False` ensures we iterate from leaves to root
        for file in files:
            file_path = os.path.join(root, file)
            if is_stale(file_path, threshold_minutes):
                try:
                    os.remove(file_path)
                    print(f"Deleted stale file: {file_path}")
                except (OSError, Exception) as e:
                    print(f"Error deleting file {file_path}: {e}")

        for dir in dirs:
            dir_path = os.path.join(root, dir)
            if is_stale(dir_path, threshold_minutes):
                try:
                    shutil.rmtree(dir_path)
                    print(f"Deleted stale directory: {dir_path}")
                except (OSError, Exception) as e:
                    print(f"Error deleting directory {dir_path}: {e}")


def scheduled_cleanup():
    cleanup_path("/tmp")
    CHAT_UPLOAD_DIR = os.path.join(current_app.config["CHAT_UPLOAD_DIR"], str(current_user.id))
    cleanup_path(CHAT_UPLOAD_DIR)


def get_uploaded_files_for_user():
    user_upload_dir = os.path.join(current_app.config["CHAT_UPLOAD_DIR"], str(current_user.id))
    if not os.path.exists(user_upload_dir):
        return []

    allowed_extensions = (".txt", ".pdf", ".docx")
    return [
        f
        for f in os.listdir(user_upload_dir)
        if os.path.isfile(os.path.join(user_upload_dir, f)) and f.endswith(allowed_extensions)
    ]
