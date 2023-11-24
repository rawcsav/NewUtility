import uuid
from datetime import datetime, timedelta

import requests
from flask import Flask, request, jsonify, Blueprint, render_template, \
    after_this_request, send_file, current_app
import openai
import os
from flask_login import login_required, current_user
from werkzeug.exceptions import NotFound

from app.database import GeneratedImage, db, UserAPIKey, User
from app.util.forms_util import GenerateImageForm
from app.util.session_util import decrypt_api_key

bp = Blueprint('image', __name__, url_prefix='/image')


@bp.route('/generate_image', methods=['GET', 'POST'])
@login_required
def generate_image():
    form = GenerateImageForm()
    image_urls = []
    error_message = None

    if form.validate_on_submit():
        try:
            prompt = form.prompt.data
            model = form.model.data or 'dall-e-3'
            n = form.n.data or 1
            size = form.size.data or '1024x1024'
            key_id = current_user.selected_api_key_id
            user_api_key = UserAPIKey.query.filter_by(user_id=current_user.id,
                                                      id=key_id).first()
            api_key = decrypt_api_key(user_api_key.encrypted_api_key)

            openai.api_key = api_key

            request_params = {
                'model': model,
                'prompt': prompt,
                'n': n,
                'size': size
            }

            if model.startswith('dall-e-3'):
                quality = form.quality.data
                style = form.style.data

                if quality:
                    request_params['quality'] = quality
                if style:
                    request_params['style'] = style

            response = openai.images.generate(**request_params)

            for image_response in response.data:
                image_url = image_response.url
                image_urls.append(image_url)
                new_image = GeneratedImage(
                    user_id=current_user.id,
                    prompt=prompt,
                    model=model,
                    image_url=image_url,
                    created_at=datetime.utcnow(),
                )
                db.session.add(new_image)
            db.session.commit()

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'image_urls': image_urls,
                    'status': 'success'
                })
        except Exception as e:
            error_message = str(e)
            print(f"Error generating image: {error_message}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'error_message': error_message,
                    'status': 'error'
                })

            return render_template(
                'image.html',
                form=form,
                image_urls=image_urls,
                error_message=error_message
            )

    return render_template(
        'image.html',
        form=form,
        image_urls=image_urls,
        error_message=error_message
    )


@bp.route('/download_image/<path:image_url>')
@login_required
def download_image(image_url):
    image_record = GeneratedImage.query.filter_by(user_id=current_user.id,
                                                  image_url=image_url).first()

    # If the image URL does not exist in the database, return an error
    if not image_record:
        raise NotFound("Image URL not found or does not belong to the current user")
    if image_record.temp_file_path:
        print('found')
        return send_file(image_record.temp_file_path, as_attachment=True)

    download_dir = os.path.join(current_app.root_path, 'static', 'temp_img')
    temp_file_name = str(uuid.uuid4())
    file_extension = '.png'  # Assuming the image is a PNG
    temp_file_path = os.path.join(download_dir, f"{temp_file_name}{file_extension}")
    try:
        response = requests.get(image_url, stream=True)
        response.raise_for_status()  # Raise an exception for HTTP error codes

        with open(temp_file_path, 'wb') as temp_file:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    temp_file.write(chunk)
        image_record.temp_file_path = temp_file_path
        db.session.commit()
    except requests.RequestException as e:
        db.session.rollback()
        print(f"Failed to download image: {e}")
        return "Error retrieving the image", 500

    return send_file(temp_file_path, as_attachment=True)
