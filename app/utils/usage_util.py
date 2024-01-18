import tiktoken
from flask_login import current_user

from app import db
from app.models.user_models import UserAPIKey, APIUsage
from decimal import Decimal


def num_tokens_from_string(string: str, model_name: str) -> int:
    encoding = tiktoken.encoding_for_model(model_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens


def chat_cost(model, input_tokens, completion_tokens):
    # Pricing per token for different models
    pricing = {
        "gpt-4-1106-preview": {"input_cost": 0.01, "output_cost": 0.03},
        "gpt-4-vision-preview": {"input_cost": 0.01, "output_cost": 0.03},
        "gpt-4-0613": {"input_cost": 0.03, "output_cost": 0.06},
        "gpt-4": {"input_cost": 0.03, "output_cost": 0.06},
        "gpt-4-32k": {"input_cost": 0.06, "output_cost": 0.12},
        "gpt-4-32k-0613": {"input_cost": 0.06, "output_cost": 0.12},
        "gpt-3.5-turbo-1106": {"input_cost": 0.0010, "output_cost": 0.0020},
        "gpt-3.5-turbo": {"input_cost": 0.0010, "output_cost": 0.0020},
        "gpt-3.5-turbo-16k": {"input_cost": 0.0010, "output_cost": 0.0020},
    }

    # Determine the costs based on model version
    if model not in pricing:
        raise ValueError("Unsupported model version.")

    input_cost = pricing[model]["input_cost"]
    output_cost = pricing[model]["output_cost"]

    # Calculate the total cost
    total_cost = ((input_tokens / 1000) * input_cost) + ((completion_tokens / 1000) * output_cost)
    update_usage_and_costs(current_user.id, current_user.selected_api_key_id, "chat", cost=total_cost)

    return total_cost


def embedding_cost(input_tokens: int):
    cost = (input_tokens / 1000) * 0.0001
    update_usage_and_costs(current_user.id, current_user.selected_api_key_id, "embedding", cost=cost)


def dalle_cost(model_name: str, resolution: str, num_images: int = 1, quality: str = None):
    pricing = {
        "dall-e-3": {
            "standard": {"1024x1024": 0.040, "1024x1792": 0.080, "1792x1024": 0.080},
            "hd": {"1024x1024": 0.080, "1024x1792": 0.120, "1792x1024": 0.120},
        },
        "dall-e-2": {"1024x1024": 0.020, "512x512": 0.018, "256x256": 0.016},
    }

    if model_name == "dall-e-3":
        if quality is None:
            raise ValueError("Quality must be provided for DALL·E 3.")
        if quality not in pricing[model_name] or resolution not in pricing[model_name][quality]:
            raise ValueError(f"Unsupported quality or resolution for " f"{model_name}: {quality}, {resolution}")
        cost_per_image = pricing[model_name][quality][resolution]
    elif model_name == "dall-e-2":
        if resolution not in pricing[model_name]:
            raise ValueError(f"Unsupported resolution for {model_name}: {resolution}")
        cost_per_image = pricing[model_name][resolution]
    else:
        raise ValueError(f"Unsupported model: {model_name}")

    total_cost = cost_per_image * num_images
    update_usage_and_costs(current_user.id, current_user.selected_api_key_id, "image_gen", cost=total_cost)


def update_usage_and_costs(user_id, api_key_id, usage_type, cost):
    cost = Decimal(str(cost))

    if cost < 0:
        raise ValueError("Cost must be non-negative")

    # Retrieve the API key and user from the database
    api_key = UserAPIKey.query.filter_by(id=api_key_id, user_id=user_id).first()

    if not api_key:
        raise ValueError("API key not found")

    # Increment usage based on the usage type
    if usage_type == "image_gen":
        api_key.usage_image_gen += cost
    elif usage_type == "chat":
        api_key.usage_chat += cost
    elif usage_type == "embedding":
        api_key.usage_embedding += cost
    elif usage_type == "audio":
        api_key.usage_audio += cost
    else:
        raise ValueError("Invalid usage type")

    # Retrieve the single APIUsage entry for this user
    api_usage_entry = APIUsage.query.filter_by(user_id=user_id).first()

    if not api_usage_entry:
        # If there's no existing entry, create one
        api_usage_entry = APIUsage(user_id=user_id, usage_image_gen=0, usage_chat=0, usage_embedding=0, usage_audio=0)
        db.session.add(api_usage_entry)

    # Update the APIUsage entry with the new cost
    if usage_type == "image_gen":
        api_usage_entry.usage_image_gen += cost
    elif usage_type == "chat":
        api_usage_entry.usage_chat += cost
    elif usage_type == "embedding":
        api_usage_entry.usage_embedding += cost
    elif usage_type == "audio":
        api_usage_entry.usage_audio += cost

    # Commit the changes to the database
    db.session.commit()


def whisper_cost(duration_seconds):
    whisper_rate_per_minute = 0.006
    duration_minutes = round(duration_seconds / 60, 2)  # Round to the nearest second
    cost = duration_minutes * whisper_rate_per_minute
    cost = round(cost, 2)
    update_usage_and_costs(current_user.id, current_user.selected_api_key_id, "audio", cost=cost)


def tts_cost(characters, model):
    rates = {"tts-1": 0.015 / 1000, "tts-1-hd": 0.030 / 1000}  # Per 1K characters rate  # Per 1K characters rate
    if model not in rates:
        raise ValueError("Invalid model type. Choose from 'whisper', 'tts', or 'tts_hd'.")
    cost = characters * rates[model]
    cost = round(cost, 2)
    update_usage_and_costs(current_user.id, current_user.selected_api_key_id, "audio", cost=cost)
