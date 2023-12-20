from time import sleep
import numpy as np
import openai
import tiktoken
from flask_login import current_user
from flask import abort
from app import db
from app.database import ChatPreferences, Message, Conversation

MODEL_TOKEN_LIMITS = {
    'gpt-4-1106-preview': 4096,
    'gpt-4-vision-preview': 4096,
    'gpt-4': 8192,
    'gpt-4-32k': 32768,
    'gpt-4-0613': 8192,
    'gpt-4-32k-0613': 32768,
    'gpt-4-0314': 8192,
    'gpt-4-32k-0314': 32768,
    'gpt-3.5-turbo-1106': 16385,
    'gpt-3.5-turbo': 4096,
    'gpt-3.5-turbo-16k': 4096,
}

ENCODING = tiktoken.get_encoding("cl100k_base")


def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def get_truncate_limit(model_name):
    model_max_tokens = MODEL_TOKEN_LIMITS.get(model_name)
    if model_max_tokens:
        return int(model_max_tokens * 0.85)
    else:
        return int(4096 * 0.85)


def get_token_count(conversation_history, encoding=ENCODING):
    num_tokens = 0
    for message in conversation_history:
        num_tokens += 5
        for key, value in message.items():
            if value:
                num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += 5
    num_tokens += 5
    return num_tokens


def truncate_conversation(conversation_history, truncate_limit):
    while True:
        if get_token_count(conversation_history, ENCODING) > truncate_limit and len(
                conversation_history) > 1:
            conversation_history.pop(1)
        else:
            break


def save_system_prompt(user_id, conversation_id, system_prompt):
    conversation = Conversation.query.filter_by(user_id=user_id,
                                                id=conversation_id).first()
    if conversation:
        conversation.system_prompt = system_prompt
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e


def get_user_conversation(user_id, conversation_id):
    conversation = Conversation.query.filter_by(user_id=user_id,
                                                id=conversation_id).first()
    if conversation:
        conversation_history = []
        system_prompt = conversation.system_prompt
        if system_prompt:
            conversation_history.append({
                "role": "system",
                "content": system_prompt,
            })

        messages = Message.query.filter_by(conversation_id=conversation.id).all()
        for message in messages:
            conversation_history.append({
                "role": "assistant" if message.direction == 'incoming' else "user",
                "content": message.content,
            })

        return conversation, conversation_history
    else:
        return None, []


def user_history(user_id, conversation_id):
    conversation = Conversation.query.filter_by(user_id=user_id,
                                                id=conversation_id).first()
    if conversation:
        conversation_history = []
        system_prompt = conversation.system_prompt
        if system_prompt:
            conversation_history.append({
                "role": "system",
                "content": system_prompt,
                "id": conversation_id,
            })

        messages = Message.query.filter_by(conversation_id=conversation.id).all()
        for message in messages:
            conversation_history.append({
                "role": "assistant" if message.direction == 'incoming' else "user",
                "content": message.content,
                "id": message.id,
            })

        return conversation, conversation_history
    else:
        return None, []


def get_user_preferences(user_id):
    preferences = ChatPreferences.query.filter_by(user_id=user_id).first()

    if preferences:
        model_name = preferences.model if preferences.model else 'gpt-3.5-turbo'
        max_token_limit = MODEL_TOKEN_LIMITS.get(model_name, 4096)
        model_max_tokens = int(max_token_limit * 0.5)
        truncate_limit = get_truncate_limit(model_name)

        # Use the preferences max_tokens if set, otherwise use the model_max_tokens
        max_tokens = preferences.max_tokens if preferences.max_tokens else model_max_tokens

        return {
            "model": model_name,
            "temperature": preferences.temperature,
            "max_tokens": max_tokens,
            "frequency_penalty": preferences.frequency_penalty,
            "presence_penalty": preferences.presence_penalty,
            "top_p": preferences.top_p,
            "stream": preferences.stream,
            "truncate_limit": truncate_limit,
        }
    else:
        return {
            "model": 'gpt-3.5-turbo',
            "temperature": 0.7,
            "max_tokens": 2048,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
            "top_p": 1.0,
            "stream": True,
            "truncate_limit": int(4096 * 0.85),
        }


# Utility function to save a message to the database
def save_message(conversation_id, content, direction, model, is_knowledge_query=False,
                 is_error=False):
    message = Message(
        conversation_id=conversation_id,
        content=content,
        direction=direction,
        model=model,
        is_knowledge_query=is_knowledge_query,
        is_error=is_error,
    )
    db.session.add(message)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e


def chat_stream(prompt, client, user_id, conversation_id):
    # Retrieve the user's conversation history and preferences
    conversation, conversation_history = get_user_conversation(user_id, conversation_id)
    if not conversation:
        print("No conversation found for user.")
        return
    if conversation.user_id != current_user.id:
        abort(403)  # HTTP 403 Forbidden
    else:
        conversation.is_interrupted = False
        db.session.commit()
        preferences = get_user_preferences(user_id)

        # Apply truncation to the conversation history if needed
        truncate_limit = preferences.get("truncate_limit")
        if truncate_limit:
            truncate_conversation(conversation_history, truncate_limit)

        # Prepare the API request payload
        request_payload = {
            "model": preferences["model"],
            "messages": conversation_history + [{"role": "user", "content": prompt}],
            "temperature": preferences["temperature"],
            "max_tokens": preferences["max_tokens"],
            "frequency_penalty": preferences["frequency_penalty"],
            "presence_penalty": preferences["presence_penalty"],
            "top_p": preferences["top_p"],
            "stream": True,
        }

        # Log the request payload for debugging
        save_message(conversation_id, prompt, 'outgoing', preferences['model'])

        full_response = ""  # Initialize a variable to accumulate the full response
        try:
            response = client.chat.completions.create(**request_payload)

            for part in response:
                db.session.commit()
                conversation = Conversation.query.get(
                    conversation_id)  # Re-fetch the conversation object
                db.session.refresh(conversation)
                if conversation.is_interrupted:
                    print("Conversation has been interrupted.")
                    conversation.is_interrupted = False
                    db.session.commit()
                    break

                content = part.choices[0].delta.content
                if content:
                    full_response += content
                    yield content

            # Save the response, whether full or partial
            if full_response.strip():  # Save only if there's non-empty content
                save_message(conversation_id, full_response, 'incoming',
                             preferences['model'])


        except Exception as e:
            error_message = handle_stream_error(e, conversation_id,
                                                preferences['model'])
            yield error_message


def chat_nonstream(prompt, client, user_id, conversation_id):
    conversation, conversation_history = get_user_conversation(user_id, conversation_id)
    if not conversation:
        print("No conversation found for user.")
        return
    if conversation.user_id != current_user.id:
        abort(403)
    else:
        preferences = get_user_preferences(user_id)
        truncate_limit = preferences["truncate_limit"]
        full_response = ""
        save_message(conversation_id, prompt, 'outgoing', preferences['model'])
        truncate_conversation(conversation_history, truncate_limit)
        try:
            response = client.chat.completions.create(
                model=preferences["model"],
                messages=conversation_history + [{"role": "user", "content": prompt}],
                temperature=preferences["temperature"],
                max_tokens=preferences["max_tokens"],
                frequency_penalty=preferences["frequency_penalty"],
                presence_penalty=preferences["presence_penalty"],
                top_p=preferences["top_p"],
                stream=False,
            )
            if response:
                full_response = response.choices[0].message.content
                if full_response.strip():
                    save_message(conversation_id, full_response, 'incoming',
                                 preferences['model'])
                return full_response
        except Exception as e:
            error_message = handle_nonstream_error(e, conversation_id,
                                                   preferences['model'])
            return error_message


# Helper functions to handle errors in streaming and non-streaming modes
def handle_stream_error(e, conversation_id, model):
    error_message = f"An error occurred: {e}"
    save_message(conversation_id, error_message, 'incoming', model, is_error=True)
    return error_message


def handle_nonstream_error(e, conversation_id, model):
    error_message = f"An error occurred: {e}"
    save_message(conversation_id, error_message, 'incoming', model, is_error=True)
    return error_message
