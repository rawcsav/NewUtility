import os
from app.models.task_models import Task, ImageTask
from app.modules.image.image_util import generate_images, save_image_to_db, download_and_store_image
from app.modules.auth.auth_util import task_client

from app.utils.tasks.task_logging import setup_logging
from config import appdir

logger = setup_logging()


def process_image(session, image_task, user_id):
    try:
        request_params = {
            "model": image_task.model,
            "prompt": image_task.prompt,
            "n": image_task.n,
            "size": image_task.size,
            "quality": image_task.quality,
            "style": image_task.style,
        }
        client, key_id, error = task_client(session, user_id)
        if error:
            logger.error(f"Client error for user {user_id}: {error}")
            raise Exception(error)

        logger.info(f"Request parameters for image generation: {request_params}")
        user_image_directory = os.path.join(appdir, "static", "user_files", "temp_img")

        image_data = generate_images(
            session=session, user_id=user_id, api_key_id=key_id, client=client, request_params=request_params
        )

        if not image_data:
            logger.error(f"No image data received for task_id={image_task.task_id}")
            return

        for image_response in image_data:
            image_url = image_response.url
            if not image_url:
                logger.error(f"No image URL received for task_id={image_task.task_id}")
                continue

            image_id = save_image_to_db(
                session,
                user_id,
                image_task.prompt,
                image_task.model,
                image_task.size,
                image_task.quality,
                image_task.style,
                image_task.task_id,
            )
            if not image_id:
                logger.error(f"Failed to save image metadata to DB for task_id={image_task.task_id}")
                continue

            local_image_url = download_and_store_image(user_image_directory, image_url, image_id)
            if local_image_url:
                return local_image_url
            else:
                logger.error(
                    f"Failed to download and store image for task_id={image_task.task_id} and image_id={image_id}"
                )
                continue

        logger.info(f"Image processing completed for task_id={image_task.task_id}")

    except Exception as e:
        logger.error(f"Error processing image for task_id={image_task.task_id}: {e}")
        raise e


def process_image_task(session, task_id):
    task = session.query(Task).get(task_id)
    image_task = session.query(ImageTask).filter_by(task_id=task_id).first()
    if task and image_task:
        try:
            logger.info(f"Processing image task {task_id} for user {task.user_id}")
            success = process_image(session, image_task, task.user_id)
            if success:
                logger.info(f"Task {task_id} status updated to completed")
                return True
            else:
                logger.error(f"Task {task_id} failed during processing")
                return False
        except Exception as e:
            session.rollback()
            logger.error(f"Error processing image task {task_id}: {e}")
            return False
    else:
        logger.error(f"Task {task_id} is not pending or image task not found")
        return False
