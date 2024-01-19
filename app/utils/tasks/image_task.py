import os

from flask import current_app

from app import create_app, db
from app.models.task_models import Task, ImageTask
from app.modules.image.image_util import generate_images, save_image_to_db, download_and_store_image
from app.modules.auth.auth_util import initialize_openai_client


def process_image(image_task, user_id):
    try:
        # Prepare request parameters for image generation
        request_params = {
            "model": image_task.model,
            "prompt": image_task.prompt,
            "n": image_task.n,
            "size": image_task.size,
            "quality": image_task.quality,
            "style": image_task.style,
        }

        # Initialize OpenAI client
        client, error = initialize_openai_client(user_id)
        if error:
            raise Exception(error)

        image_data = generate_images(client, request_params)

        download_dir = current_app.config["USER_IMAGE_DIRECTORY"]

        for image_response in image_data:
            image_url = image_response.url
            image_id = save_image_to_db(
                user_id,
                image_task.prompt,
                image_task.model,
                image_task.size,
                image_task.quality,
                image_task.style,
                image_task.task_id,
            )
            download_and_store_image(download_dir, image_url, image_id)

    except Exception as e:
        print(f"Error processing image task {image_task.id}: {e}")
        image_task.task.status = "failed"
        db.session.commit()
        return

    # Mark the task as completed
    image_task.task.status = "completed"
    db.session.commit()


def process_image_task(task_id):
    app = create_app()
    with app.app_context():
        task = Task.query.get(task_id)
        image_task = ImageTask.query.filter_by(task_id=task.id, user_id=task.user_id).first()

        if task and image_task and task.status == "pending":
            process_image(image_task)
            db.session.commit()
