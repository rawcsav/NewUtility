import os
from datetime import datetime
import requests
from PIL import Image
from flask import url_for
from app.models.image_models import GeneratedImage
from app.utils.usage_util import dalle_cost


def download_compressed_image(download_dir, image_url, image_id):
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    file_extension = ".png"
    temp_file_name = f"{image_id}{file_extension}"
    temp_file_path = os.path.join(download_dir, temp_file_name)

    try:
        response = requests.get(image_url, stream=True)
        response.raise_for_status()

        with open(temp_file_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)

        webp_file_name = f"{image_id}.webp"
        webp_file_path = os.path.join(download_dir, webp_file_name)

        image = Image.open(temp_file_path)
        image.save(webp_file_path, "WEBP")

        os.remove(temp_file_path)

        return webp_file_path

    except requests.RequestException as e:
        return None


def generate_images(session, user_id, api_key_id, client, request_params):
    response = client.images.generate(**request_params)
    if response is None or not hasattr(response, "data"):
        raise Exception("Failed to generate img")
    dalle_cost(
        session=session,
        user_id=user_id,
        api_key_id=api_key_id,
        model_name=request_params["model"],
        resolution=request_params["size"],
        num_images=request_params["n"],
        quality=request_params.get("quality"),
    )
    return response.data


def save_image_to_db(session, user_id, prompt, model, size, quality, style, task_id):
    new_image = GeneratedImage(
        user_id=user_id,
        prompt=prompt,
        model=model,
        created_at=datetime.utcnow(),
        size=size,
        quality=quality,
        style=style,
        task_id=task_id,
    )
    session.add(new_image)
    session.flush()
    return new_image.id


def download_and_store_image(download_dir, image_url, uuid):
    local_image_url = download_compressed_image(download_dir, image_url, uuid)
    return local_image_url
