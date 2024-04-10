from urllib.parse import urlparse
import tiktoken
from flask import abort, stream_with_context
from flask_login import current_user

from app import db
from app.models.chat_models import MessageChunkAssociation, Conversation, Message, ChatPreferences
from app.utils.usage_util import chat_cost, num_tokens_from_string

MODEL_TOKEN_LIMITS = {
    "gpt-4-1106-preview": 4096,
    "gpt-4-vision-preview": 4096,
    "gpt-4": 8192,
    "gpt-4-32k": 32768,
    "gpt-4-0613": 8192,
    "gpt-4-32k-0613": 32768,
    "gpt-3.5-turbo-1106": 16385,
    "gpt-3.5-turbo": 4096,
    "gpt-3.5-turbo-16k": 4096,
}

ENCODING = tiktoken.get_encoding("cl100k_base")


def chat_truncate_limit(model_name):
    model_max_tokens = MODEL_TOKEN_LIMITS.get(model_name)
    if model_max_tokens:
        return int(model_max_tokens * 0.85)
    else:
        return int(4096 * 0.85)


def chat_tokens(conversation_history, encoding=ENCODING):
    num_tokens = 0
    for message in conversation_history:
        num_tokens += 5  # Assuming 5 tokens for the role separator or similar
        content = message.get("content")
        if isinstance(content, str):
            num_tokens += len(encoding.encode(content))
        elif isinstance(content, dict) and content.get("type") == "text":
            # Only encode the 'text' part of the content if it's a dict
            text_content = content.get("text", "")
            num_tokens += len(encoding.encode(text_content))
        elif isinstance(content, list):
            # If the content is a list, iterate over it and encode text elements
            for item in content:
                if item.get("type") == "text":
                    text_content = item.get("text", "")
                    num_tokens += len(encoding.encode(text_content))
    return num_tokens


def truncate_conversation(conversation_history, truncate_limit):
    while True:
        if chat_tokens(conversation_history, ENCODING) > truncate_limit and len(conversation_history) > 1:
            conversation_history.pop(1)
        else:
            break


def get_user_conversation(user_id, conversation_id):
    conversation = Conversation.query.filter_by(user_id=user_id, id=conversation_id, delete=False).first()
    preferences = get_user_preferences(user_id)

    if conversation:
        conversation_history = []
        system_prompt = conversation.system_prompt
        if system_prompt:
            conversation_history.append({"role": "system", "content": system_prompt})

        messages = Message.query.filter_by(conversation_id=conversation_id).order_by(Message.created_at.asc()).all()
        for message in messages:
            message_content = message.content

            conversation_history.append(
                {"role": "assistant" if message.direction == "incoming" else "user", "content": message_content}
            )

        return conversation, conversation_history
    else:
        return None, []


def get_user_history(user_id, conversation_id):
    conversation = Conversation.query.filter_by(user_id=user_id).first()
    preferences = get_user_preferences(user_id)

    if conversation:
        conversation_history = []
        system_prompt = conversation.system_prompt
        if system_prompt:
            conversation_history.append({"role": "system", "content": system_prompt, "id": conversation_id})

        messages = Message.query.filter_by(conversation_id=conversation_id).order_by(Message.created_at.asc()).all()
        for message in messages:
            message_dict = {
                "id": message.id,
                "role": "assistant" if message.direction == "incoming" else "user",
                "content": message.content,
            }

            conversation_history.append(message_dict)

        return conversation, conversation_history


def get_user_preferences(user_id):
    preferences = ChatPreferences.query.filter_by(user_id=user_id).first()

    if preferences:
        model_name = preferences.model if preferences.model else "gpt-3.5-turbo"
        max_token_limit = MODEL_TOKEN_LIMITS.get(model_name, 4096)
        model_max_tokens = int(max_token_limit * 0.5)
        truncate_limit = chat_truncate_limit(model_name)

        max_tokens = preferences.max_tokens if preferences.max_tokens else model_max_tokens

        return {
            "model": model_name,
            "temperature": preferences.temperature,
            "max_tokens": max_tokens,
            "frequency_penalty": preferences.frequency_penalty,
            "presence_penalty": preferences.presence_penalty,
            "top_p": preferences.top_p,
            "truncate_limit": truncate_limit,
        }
    else:
        return {
            "model": "gpt-3.5-turbo",
            "temperature": 0.7,
            "max_tokens": 2048,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
            "top_p": 1.0,
            "truncate_limit": int(4096 * 0.85),
        }


def save_message(
    conversation_id,
    content,
    direction,
    model,
    is_knowledge_query=False,
    is_error=False,
    chunk_ids=None,  # Optional parameter for multiple chunk IDs (list)
    similarity_ranks=None,  # Optional parameter for multiple similarity rankings (list)
):
    message = Message(
        conversation_id=conversation_id,
        content=content,
        direction=direction,
        model=model,
        is_knowledge_query=is_knowledge_query,
        is_error=is_error,
    )
    db.session.add(message)
    db.session.flush()

    try:
        if chunk_ids and similarity_ranks and (len(chunk_ids) == len(similarity_ranks)):
            message.is_knowledge_query = True
            for chunk_id, similarity_rank in zip(chunk_ids, similarity_ranks):
                chunk_association = MessageChunkAssociation(
                    message_id=message.id, chunk_id=chunk_id, similarity_rank=similarity_rank
                )
                db.session.add(chunk_association)

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e


def is_development_url(url):
    parsed_url = urlparse(url)
    if parsed_url.hostname == "localhost" or parsed_url.hostname == "127.0.0.1":
        return True
    if parsed_url.port == 8080:
        return True
    return False


# Global dictionary to track interruptions, keyed by conversation_id
interruption_flags = {}


def set_interruption_flag(conversation_id):
    interruption_flags[conversation_id] = True


def clear_interruption_flag(conversation_id):
    interruption_flags[conversation_id] = False


def check_interruption_flag(conversation_id):
    return interruption_flags.get(conversation_id, False)


def chat_stream(raw_prompt, prompt, client, user_id, conversation_id, retry=False, chunk_associations=None):
    conversation, conversation_history = get_user_conversation(user_id, conversation_id)
    if not conversation:
        return
    if conversation.user_id != current_user.id:
        abort(403)
    else:
        clear_interruption_flag(conversation_id)
        preferences = get_user_preferences(user_id)
        user_message_content = prompt
        truncate_limit = preferences.get("truncate_limit")
        if truncate_limit:
            truncate_conversation(conversation_history, truncate_limit)
        if preferences["model"] == "gpt-4-1106-preview":
            model = "gpt-4-turbo-preview"
        else:
            model = preferences["model"]
        request_payload = {
            "model": model,
            "messages": conversation_history + [{"role": "user", "content": user_message_content}],
            "temperature": preferences["temperature"],
            "max_tokens": preferences["max_tokens"],
            "frequency_penalty": preferences["frequency_penalty"],
            "presence_penalty": preferences["presence_penalty"],
            "top_p": preferences["top_p"],
            "stream": True,
        }
        if retry:
            if conversation_history and conversation_history[-1]["role"] == "user":
                conversation_history.pop()
        else:
            if chunk_associations is not None:
                save_message(
                    conversation_id,
                    raw_prompt,
                    "outgoing",
                    preferences["model"],
                    chunk_ids=[chunk_id for chunk_id, _ in chunk_associations],
                    similarity_ranks=[rank for _, rank in chunk_associations],
                )
            else:
                save_message(conversation_id, raw_prompt, "outgoing", preferences["model"])
        full_response = ""
        try:
            response = client.chat.completions.create(**request_payload)

            for part in response:
                if check_interruption_flag(conversation_id):
                    clear_interruption_flag(conversation_id)
                    break

                content = part.choices[0].delta.content
                if content:
                    full_response += content
                    yield content

            total_prompt_tokens = num_tokens_from_string(prompt, preferences["model"])
            total_completion_tokens = num_tokens_from_string(full_response, preferences["model"])

            chat_cost(
                session=db.session,
                user_id=current_user.id,
                api_key_id=current_user.selected_api_key_id,
                model=preferences["model"],
                input_tokens=total_prompt_tokens,
                completion_tokens=total_completion_tokens,
            )

            if full_response.strip():
                save_message(conversation_id, full_response, "incoming", preferences["model"])

        except Exception as e:
            error_message = f"An error occurred: {e}"
            yield error_message


def handle_stream(raw_prompt, prompt, client, user_id, conversation_id, retry=False, chunk_associations=None):
    full_response = ""

    def generate():
        nonlocal full_response
        for content in chat_stream(raw_prompt, prompt, client, user_id, conversation_id, retry, chunk_associations):
            full_response += content
            yield content

    return stream_with_context(generate()), full_response


def retry_delete_messages(conversation_id, message_id):
    try:
        message_to_retry = Message.query.get_or_404(message_id)
        if message_to_retry.conversation_id != conversation_id:
            raise ValueError("Message ID does not match the conversation ID.")
        Message.query.filter(
            Message.conversation_id == conversation_id, Message.created_at > message_to_retry.created_at
        ).delete()
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        raise e
