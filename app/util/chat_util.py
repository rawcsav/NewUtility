import base64
import os
import uuid
from datetime import datetime
from time import sleep
import numpy as np
import openai
import tiktoken
from PIL import Image
from flask_login import current_user
from flask import abort, stream_with_context, current_app, url_for
from app import db
from app.database import ChatPreferences, Message, Conversation, MessageImages
from app.util.usage_util import chat_cost, update_usage_and_costs, \
    num_tokens_from_string

MODEL_TOKEN_LIMITS = {
    'gpt-4-1106-preview': 4096,
    'gpt-4-vision-preview': 4096,
    'gpt-4': 8192,
    'gpt-4-32k': 32768,
    'gpt-4-0613': 8192,
    'gpt-4-32k-0613': 32768,
    'gpt-3.5-turbo-1106': 16385,
    'gpt-3.5-turbo': 4096,
    'gpt-3.5-turbo-16k': 4096,
}

ENCODING = tiktoken.get_encoding("cl100k_base")


def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


# Function to determine the image quality
def get_image_quality(image_path):
    with Image.open(image_path) as img:
        width, height = img.size
        return 'high' if max(width, height) > 512 else 'low'


# Function to encode a local image to base64
def encode_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def get_truncate_limit(model_name):
    model_max_tokens = MODEL_TOKEN_LIMITS.get(model_name)
    if model_max_tokens:
        return int(model_max_tokens * 0.85)
    else:
        return int(4096 * 0.85)


def get_token_count(conversation_history, encoding=ENCODING):
    num_tokens = 0
    for message in conversation_history:
        num_tokens += 5  # Assuming 5 tokens for the role separator or similar
        content = message.get('content')
        if isinstance(content, str):
            num_tokens += len(encoding.encode(content))
        elif isinstance(content, dict) and content.get('type') == 'text':
            # Only encode the 'text' part of the content if it's a dict
            text_content = content.get('text', '')
            num_tokens += len(encoding.encode(text_content))
        elif isinstance(content, list):
            # If the content is a list, iterate over it and encode text elements
            for item in content:
                if item.get('type') == 'text':
                    text_content = item.get('text', '')
                    num_tokens += len(encoding.encode(text_content))
        # If there are other content types that need to be handled, add them here
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
            message_content = message.content  # Default to a string for text-only messages

            # If the message has associated images, construct the image payload
            if message.is_vision:
                image_records = MessageImages.query.filter_by(
                    message_id=message.id).all()
                # Only construct the payload if there are images
                if image_records:
                    image_urls = [image.image_url for image in image_records]
                    image_payloads = get_image_payload(image_urls)
                    # Combine text and image payloads into a list
                    message_content = [{"type": "text", "text": message.content}]
                    message_content.extend(image_payloads)

            conversation_history.append({
                "role": "assistant" if message.direction == 'incoming' else "user",
                "content": message_content,
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
            message_dict = {
                "id": message.id,
                "role": "assistant" if message.direction == 'incoming' else "user",
                "content": message.content,
            }

            # If the message has associated images, add their URLs
            if message.is_vision:
                image_records = MessageImages.query.filter_by(
                    message_id=message.id).all()
                message_dict['images'] = [image.image_url for image in image_records]

            conversation_history.append(message_dict)

        return conversation, conversation_history


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


def save_message(conversation_id, content, direction, model,
                 is_knowledge_query=False, is_error=False, images=None):
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
        if images:
            for filename in images:
                image_uuid = filename.rsplit('/', 1)[-1].rsplit('.', 1)[0]

                image_record = MessageImages.query.filter_by(uuid=image_uuid).first()
                if image_record:
                    image_record.message_id = message.id
                    message.is_vision = True
                    db.session.add(image_record)

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e


import requests


def get_image_payload(images):
    image_payloads = []
    for image in images:
        if image.startswith(('http://', 'https://')):
            response = requests.get(image)
            response.raise_for_status()
            encoded_image = base64.b64encode(response.content).decode('utf-8')
            image_payloads.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/webp;base64,{encoded_image}"
                }
            })
        elif os.path.isfile(image):
            encoded_image = encode_image_to_base64(image)
            image_payloads.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/webp;base64,{encoded_image}"
                }
            })
        else:
            raise ValueError(f"Invalid image path or URL provided: {image}")
    return image_payloads


def associate_images_with_message(message_id, image_uuids):
    for image_uuid in image_uuids:
        # Find the image record by UUID
        image_record = MessageImages.query.filter_by(uuid=image_uuid).first()
        if image_record:
            # Update the image record with the message_id
            image_record.message_id = message_id
            db.session.add(image_record)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e


def chat_stream(prompt, client, user_id, conversation_id, images=None):
    conversation, conversation_history = get_user_conversation(user_id, conversation_id)
    if not conversation:
        print("No conversation found for user.")
        return
    if conversation.user_id != current_user.id:
        abort(403)
    else:
        conversation.is_interrupted = False
        db.session.commit()
        preferences = get_user_preferences(user_id)

        if preferences["model"] == "gpt-4-vision-preview" and images:
            image_payloads = get_image_payload(images)
            user_message_content = [{"type": "text", "text": prompt}]
            user_message_content.extend(image_payloads)
        else:
            user_message_content = prompt
        truncate_limit = preferences.get("truncate_limit")
        if truncate_limit:
            truncate_conversation(conversation_history, truncate_limit)

        # Prepare the API request payload
        request_payload = {
            "model": preferences["model"],
            "messages": conversation_history + [
                {"role": "user", "content": user_message_content}],
            "temperature": preferences["temperature"],
            "max_tokens": preferences["max_tokens"],
            "frequency_penalty": preferences["frequency_penalty"],
            "presence_penalty": preferences["presence_penalty"],
            "top_p": preferences["top_p"],
            "stream": True,
        }

        # Log the request payload for debugging
        save_message(conversation_id, prompt, 'outgoing', preferences['model'],
                     images=images)

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

            total_prompt_tokens = num_tokens_from_string(prompt, preferences['model'])
            total_completion_tokens = num_tokens_from_string(full_response,
                                                             preferences['model'])

            # After the chat is completed, calculate the cost based on token counts
            cost = chat_cost(preferences["model"], total_prompt_tokens,
                             total_completion_tokens)
            update_usage_and_costs(user_id=user_id,
                                   api_key_id=current_user.selected_api_key_id,
                                   usage_type='chat',
                                   cost=cost)

            # Save the response, whether full or partial
            if full_response.strip():  # Save only if there's non-empty content
                save_message(conversation_id, full_response, 'incoming',
                             preferences['model'])


        except Exception as e:
            error_message = handle_stream_error(e, conversation_id,
                                                preferences['model'])
            yield error_message


def chat_nonstream(prompt, client, user_id, conversation_id, images=None):
    conversation, conversation_history = get_user_conversation(user_id, conversation_id)
    if not conversation:
        print("No conversation found for user.")
        return
    if conversation.user_id != current_user.id:
        abort(403)
    else:
        preferences = get_user_preferences(user_id)

        if preferences["model"] == "gpt-4-vision-preview" and images:
            image_payloads = get_image_payload(images)
            user_message_content = [{"type": "text", "text": prompt}]
            user_message_content.extend(image_payloads)
        else:
            user_message_content = prompt

        truncate_limit = preferences["truncate_limit"]
        full_response = ""
        save_message(conversation_id, prompt, 'outgoing', preferences['model'],
                     images=images)
        truncate_conversation(conversation_history, truncate_limit)
        try:
            response = client.chat.completions.create(
                model=preferences["model"],
                messages=conversation_history + [
                    {"role": "user", "content": user_message_content}],
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

                    # Use the token counts from the response to calculate the cost
                    prompt_tokens = response.usage.prompt_tokens
                    completion_tokens = response.usage.completion_tokens
                    cost = chat_cost(preferences["model"], prompt_tokens,
                                     completion_tokens)
                    update_usage_and_costs(user_id=user_id,
                                           api_key_id=current_user.selected_api_key_id,
                                           usage_type='chat',
                                           cost=cost)
                return full_response
        except Exception as e:
            error_message = handle_nonstream_error(e, conversation_id,
                                                   preferences['model'])
            return error_message


def handle_stream(prompt, client, user_id, conversation_id, images=None):
    full_response = ""

    def generate():
        nonlocal full_response
        conversation = Conversation.query.get(conversation_id)
        for content in chat_stream(prompt, client, user_id, conversation_id, images):
            full_response += content
            yield content

    return stream_with_context(generate()), full_response


def handle_nonstream(prompt, client, user_id, conversation_id, images=None):
    return chat_nonstream(prompt, client, user_id, conversation_id, images)


def handle_stream_error(e, conversation_id, model):
    error_message = f"An error occurred: {e}"
    return error_message


def handle_nonstream_error(e, conversation_id, model):
    error_message = f"An error occurred: {e}"
    return error_message


# Utility function to delete messages after a specified message ID.
def retry_delete_messages(conversation_id, message_id):
    try:
        # Find the message to use as a reference point for deletion
        message_to_retry = Message.query.get_or_404(message_id)
        if message_to_retry.conversation_id != conversation_id:
            raise ValueError("Message ID does not match the conversation ID.")

        # Delete messages that come after the specified message
        Message.query.filter(
            Message.conversation_id == conversation_id,
            Message.created_at >= message_to_retry.created_at
        ).delete()
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        raise e


def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_image(file_stream):
    # Generate a unique UUID for the image file
    image_uuid = str(uuid.uuid4())
    webp_file_name = f"{image_uuid}.webp"
    webp_file_path = os.path.join(current_app.config['CHAT_IMAGE_DIRECTORY'],
                                  webp_file_name)

    # Convert the image to WEBP and save it
    image = Image.open(file_stream).convert("RGB")
    image.save(webp_file_path, 'WEBP')

    return image_uuid, webp_file_name


def get_image_url(webp_file_name):
    return url_for('static', filename=f'user_img/{webp_file_name}', _external=True)
