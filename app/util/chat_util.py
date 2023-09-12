import concurrent.futures
import os
import re
import time
from typing import Dict, Tuple, List

import docx2txt
import openai
import pandas as pd
import tiktoken
from PyPDF2 import PdfReader
from nltk.tokenize import word_tokenize, sent_tokenize
from scipy import spatial

from app.config import EMBEDDING_MODEL, TOP_N, MAX_LENGTH, GPT_MODEL


def get_first_10_words(text):
    words = word_tokenize(text)
    return ' '.join(words[:10])


def num_tokens(text: str, model: str = GPT_MODEL) -> int:
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))


def preprocess_text(text):
    # Remove copyright and source information
    text = re.sub(r'©.*?\n', '', text)

    # Remove download instructions
    text = re.sub(r'Download : Download full-size image', '', text)

    # Replace newline characters with space
    text = re.sub(r'\n', ' ', text)

    # Replace multiple spaces with a single space
    text = re.sub(r'\s+', ' ', text)

    return text


def split_text(text, document_title):
    text = preprocess_text(text)
    sentences = sent_tokenize(text)

    sections = []
    current_section = {"title": document_title, "loc": "", "text": "", "tokens": 0}
    current_sentences = []

    for sentence in sentences:
        tokens_count = num_tokens(sentence)

        if current_section["tokens"] + tokens_count > MAX_LENGTH:
            current_section["text"] = ' '.join(current_sentences)
            current_section["loc"] = get_first_10_words(current_section["text"])
            sections.append(current_section)
            current_sentences = [sentence]
            current_section = {"title": document_title, "loc": "", "text": "", "tokens": tokens_count}
        else:
            current_sentences.append(sentence)
            current_section["tokens"] += tokens_count

    if current_sentences:
        current_section["text"] = ' '.join(current_sentences)
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
            with open(filepath, 'rb') as file:
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
        txt_filepath = os.path.splitext(filepath)[0] + '.txt'
        with open(txt_filepath, 'w', encoding="utf-8") as txt_file:
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

            with open(filepath, 'r', encoding="utf-8") as file:
                extracted_text = file.read()

            original_title = os.path.splitext(filename)[0]
            sections = split_text(extracted_text,
                                  original_title)  # Assuming split_text is defined elsewhere in your code
            df = pd.DataFrame(sections)
            dfs.append(df)

    return pd.concat(dfs, ignore_index=True)


def get_embedding(text: str, api_key, model: str = EMBEDDING_MODEL, retry_limit=3, retry_delay=5) -> list[float]:
    openai.api_key = api_key
    for i in range(retry_limit):
        try:
            result = openai.Embedding.create(
                model=model,
                input=text
            )
            return result["data"][0]["embedding"]
        except openai.error.OpenAIError as e:
            print(f"Error: {e}")
            return None
        print(f"Retrying... (attempt {i + 1})")
        time.sleep(retry_delay)
    return None


def compute_doc_embeddings(df: pd.DataFrame, api_key, batch_size=3, num_workers=6) -> Dict[
    Tuple[str, str], List[float]]:
    api_key = api_key
    embeddings = {}

    def process_batch(batch: pd.DataFrame) -> Dict[Tuple[str, str], List[float]]:
        batch_embeddings = {}
        texts = [r.text for idx, r in batch.iterrows()]
        for j, text in enumerate(texts):
            embedding = get_embedding(text, api_key)
            if embedding is None:
                print("Failed to compute embedding for document with index:", batch.index[j])
            else:
                batch_embeddings[batch.index[j]] = embedding
        return batch_embeddings

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = []
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i + batch_size]
            futures.append(executor.submit(process_batch, batch))

        for future in concurrent.futures.as_completed(futures):
            embeddings.update(future.result())

    return embeddings


def add_embeddings_to_df(df, api_key):
    api_key = api_key
    document_embeddings = compute_doc_embeddings(df, api_key)

    df["embeddings"] = document_embeddings
    return df


def strings_ranked_by_relatedness(query: str, df: pd.DataFrame, api_key,
                                  relatedness_fn=lambda x, y: 1 - spatial.distance.cosine(x, y),
                                  top_n: int = TOP_N) -> pd.DataFrame:
    openai.api_key = api_key
    query_embedding_response = openai.Embedding.create(
        model=EMBEDDING_MODEL,
        input=query,
    )
    query_embedding = query_embedding_response["data"][0]["embedding"]

    df['relatedness'] = df['embeddings'].apply(lambda x: relatedness_fn(query_embedding, x))
    sorted_df = df.sort_values(by='relatedness', ascending=False).head(top_n)
    return sorted_df


def process_filenames(filenames: List[str]) -> List[str]:
    return [filename.replace('.txt', '') for filename in filenames]


def query_message(query: str, df: pd.DataFrame, api_key, model: str, token_budget: int, specific_documents=None) -> str:
    df['title'] = df['title'].astype(str)
    if specific_documents:
        specific_documents = process_filenames(specific_documents)
        df_filtered = df[df['title'].isin(specific_documents)]
    else:
        df_filtered = df

    sorted_df = strings_ranked_by_relatedness(query, df_filtered, api_key)
    introduction = 'Use the below textual excerpts to answer the subsequent question. If the answer cannot be found in the provided text, write "I could not find an answer."'
    question = f"\n\nQuestion: {query}"

    message = introduction
    full_message = introduction

    docs_used = []
    for _, row in sorted_df.iterrows():
        doc_info = f'\n\nTitle: {row["title"]}\nLocation: {row["loc"]}'
        next_article = doc_info + f'\nTextual excerpt section:\n"""\n{row["text"]}\n"""'
        if num_tokens(full_message + next_article + question, model=model) <= token_budget:
            message += doc_info
            full_message += next_article
            docs_used.append((row["title"], row["loc"]))
    full_message += question
    return message, full_message, docs_used


def ask(query: str, df: pd.DataFrame, api_key, model: str = GPT_MODEL, specific_documents=None):
    openai.api_key = api_key
    prompt = query
    max_tokens = 7096
    token_budget = max_tokens - num_tokens(prompt, model=model)

    message, full_message, docs_used = query_message(prompt, df, api_key, model=model, token_budget=token_budget,
                                                     specific_documents=specific_documents)

    max_tokens = max_tokens - num_tokens(prompt + full_message, model=model)
    messages = [
        {"role": "system",
         "content": "You are a knowledgeable assistant that uses information from provided textual excerpts to answer questions."},
        {"role": "user", "content": full_message},
    ]

    response_content = ""
    for chunk in openai.ChatCompletion.create(model=model, messages=messages, max_tokens=max_tokens, temperature=.5,
                                              stream=True):
        content = chunk["choices"][0].get("delta", {}).get("content", "")
        if content:
            yield content
    yield "\n\nDocuments used:\n"
    for title, loc in docs_used:
        yield f'Title: {title}\n'
