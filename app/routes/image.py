import uuid
from datetime import datetime
from flask import (
    request,
    jsonify,
    Blueprint,
    render_template,
    send_file,
    url_for,
    current_app,
)
import openai
import os
from flask_login import login_required, current_user
from werkzeug.exceptions import NotFound
from app import db
from app.database import GeneratedImage, UserAPIKey
from app.util.forms_util import GenerateImageForm
from app.util.image_util import download_and_convert_image
from app.util.session_util import decrypt_api_key
from app.util.usage_util import dalle_cost, update_usage_and_costs

bp = Blueprint("image", __name__, url_prefix="/image")


@bp.route("/generate_image", methods=["GET", "POST"])
@login_required
def generate_image():
    form = GenerateImageForm()
    uuids = []
    error_message = None
    image_urls = []

    if form.validate_on_submit():
        try:
            prompt = form.prompt.data
            model = form.model.data or "dall-e-3"
            n = form.n.data or 1
            size = form.size.data or "1024x1024"
            key_id = current_user.selected_api_key_id
            user_api_key = UserAPIKey.query.filter_by(
                user_id=current_user.id, id=key_id
            ).first()
            api_key = decrypt_api_key(user_api_key.encrypted_api_key)

            openai.api_key = api_key

            request_params = {"model": model, "prompt": prompt, "n": n, "size": size}

            if model.startswith("dall-e-3"):
                quality = form.quality.data
                style = form.style.data

                if quality:
                    request_params["quality"] = quality
                if style:
                    request_params["style"] = style
            else:
                quality = None
                style = None

            response = openai.images.generate(**request_params)
            # Check if the response is successful
            if response is not None and hasattr(response, "data"):
                cost = dalle_cost(
                    model_name=model, resolution=size, num_images=n, quality=quality
                )

                # Update the API key and APIUsage with the new cost
                update_usage_and_costs(
                    user_id=current_user.id,
                    api_key_id=key_id,
                    usage_type="image_gen",
                    cost=cost,
                )

            for image_response in response.data:
                image_url = image_response.url
                temp_uuid = str(uuid.uuid4())
                uuids.append(temp_uuid)

                new_image = GeneratedImage(
                    user_id=current_user.id,
                    prompt=prompt,
                    model=model,
                    uuid=temp_uuid,
                    created_at=datetime.utcnow(),
                )
                db.session.add(new_image)
                db.session.commit()
                download_dir = current_app.config["USER_IMAGE_DIRECTORY"]
                local_image_url = download_and_convert_image(
                    download_dir, image_url, temp_uuid
                )
                image_urls.append(local_image_url)

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"image_urls": image_urls, "status": "success"})

        except Exception as e:
            error_message = str(e)
            db.session.rollback()
            print(f"Error generating image: {error_message}")
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"error_message": error_message, "status": "error"})

    return render_template(
        "image.html", form=form, image_urls=image_urls, error_message=error_message
    )


@bp.route("/download_image/<uuid:image_uuid>")
@login_required
def download_image(image_uuid):
    image_record = GeneratedImage.query.filter_by(
        user_id=current_user.id, uuid=str(image_uuid)
    ).first()

    if not image_record:
        raise NotFound("Image not found or does not belong to the current user")

    download_dir = current_app.config["USER_IMAGE_DIRECTORY"]
    webp_file_name = f"{image_uuid}.webp"
    webp_file_path = os.path.join(download_dir, webp_file_name)

    if not os.path.exists(webp_file_path):
        raise NotFound("The requested image file does not exist.")

    return send_file(webp_file_path, as_attachment=True)


@bp.route("/history")
@login_required
def image_history():
    # Retrieve the user's images from the database ordered by 'id' descending
    user_images = (
        GeneratedImage.query.filter_by(user_id=current_user.id)
        .order_by(GeneratedImage.id.desc())
        .limit(15)
        .all()
    )

    # Create a list of image URLs and UUIDs
    image_data = [
        {
            "url": url_for(
                "static", filename=f"temp_img/{img.uuid}.webp", _external=True
            ),
            "uuid": img.uuid,
        }
        for img in user_images
    ]

    return jsonify(image_data)
