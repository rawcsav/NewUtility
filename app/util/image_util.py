import os
from datetime import datetime

from PIL import Image
from flask import url_for
import requests

from app import db
from app.database import GeneratedImage
from app.util.usage_util import update_usage_and_costs, dalle_cost


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

        webp_url = url_for(
            "static", filename=f"temp_img/{webp_file_name}", _external=True
        )
        return webp_url

    except requests.RequestException as e:
        print(f"Error downloading image: {e}")
        return None


def generate_images(client, request_params, user_id, api_key_id):
    response = client.images.generate(**request_params)
    if response is None or not hasattr(response, "data"):
        raise Exception("Failed to generate images")

    cost = dalle_cost(
        model_name=request_params["model"],
        resolution=request_params["size"],
        num_images=request_params["n"],
        quality=request_params.get("quality"),
    )
    update_usage_and_costs(user_id, api_key_id, "image_gen", cost)

    return response.data


def save_image_to_db(user_id, prompt, model, size, quality, style):
    new_image = GeneratedImage(
        user_id=user_id,
        prompt=prompt,
        model=model,
        created_at=datetime.utcnow(),
        size=size,
        quality=quality,
        style=style,
    )
    db.session.add(new_image)
    db.session.commit()
    return new_image.id  # Return the id of the new image


def download_and_store_image(download_dir, image_url, uuid):
    local_image_url = download_compressed_image(download_dir, image_url, uuid)
    return local_image_url
