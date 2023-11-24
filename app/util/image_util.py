import os
from PIL import Image
from flask import current_app, url_for
import requests
from app import db


def download_and_convert_image(image_url, image_uuid):
    download_dir = os.path.join(current_app.root_path, 'static', 'temp_img')
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    file_extension = '.png'
    temp_file_name = f"{image_uuid}{file_extension}"
    temp_file_path = os.path.join(download_dir, temp_file_name)

    try:
        response = requests.get(image_url, stream=True)
        response.raise_for_status()

        with open(temp_file_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)

        webp_file_name = f"{image_uuid}.webp"
        webp_file_path = os.path.join(download_dir, webp_file_name)

        image = Image.open(temp_file_path)
        image.save(webp_file_path, 'WEBP')

        os.remove(temp_file_path)

        webp_url = url_for('static', filename=f'temp_img/{webp_file_name}',
                           _external=True)
        return webp_url

    except requests.RequestException as e:
        print(f"Error downloading image: {e}")
        return None
