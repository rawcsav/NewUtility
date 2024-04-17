from celery import group
import os
from pathlib import Path
import soundfile as sf
from app import socketio
from app.models.audio_models import TranscriptionJob, TranscriptionJobSegment, TranslationJob, TranslationJobSegment
from app.tasks.celery_task import celery
from app.modules.user.user_util import get_user_audio_directory
from app.models.task_models import Task, TTSTask, TranscriptionTask, TranslationTask
from app.modules.audio.audio_util import generate_speech, create_job, get_audio_duration, create_transcribe_job_segment, \
    create_translate_job_segment
from app.modules.auth.auth_util import task_client
from app.utils.logging_util import configure_logging
from app.utils.task_util import make_session
from app.utils.usage_util import whisper_cost

logger = configure_logging()

def process_tts(session, tts_task, user_id):
    try:
        logger.info(f"Starting TTS processing for task_id={tts_task.task_id}")
        client, key_id, error = task_client(session, user_id)
        if error:
            raise Exception(error)
        socketio.emit(
            "task_progress",
            {"task_id": tts_task.task_id, "message": "Generating speech..."},
            room=str(user_id),
            namespace="/audio",
        )
        tts_filepath, job_id = generate_speech(
            session=session,
            client=client,
            api_key_id=key_id,
            user_id=user_id,
            model=tts_task.model,
            voice=tts_task.voice,
            input_text=tts_task.input_text,
            response_format=tts_task.response_format,
            speed=tts_task.speed,
            task_id=tts_task.task_id,
        )
        logger.info(f"TTS processing completed for task_id={tts_task.task_id}")
        socketio.emit(
            "task_complete",
            {
                "task_id": tts_task.task_id,
                "message": "TTS processing completed!",
                "status": "completed",
                "job_type": "tts",
                "job_details": {
                    "id": job_id,
                    "output_filename": os.path.basename(tts_filepath),
                    "model": tts_task.model,
                    "voice": tts_task.voice,
                    "speed": tts_task.speed,
                    "created_at": "Just now",
                },
            },
            room=str(user_id),
            namespace="/audio",
        )
        return tts_filepath
    except Exception as e:
        socketio.emit(
            "task_update",
            {"task_id": tts_task.task_id, "status": "error", "error": str(e)},
            room=str(user_id),
            namespace="/audio",
        )
        logger.error(f"Error during TTS processing for task_id={tts_task.task_id}: {e}")
        raise e


@celery.task(time_limit=200)
def process_tts_task(task_id):
    session = make_session()
    try:
        task = session.query(Task).filter_by(id=task_id).one()
        tts_task = session.query(TTSTask).filter_by(task_id=task_id).first()
        socketio.emit(
            "task_progress",
            {"task_id": task.id, "message": f"Beginning TTS task..."},
            room=str(task.user_id),
            namespace="/audio",
        )
        if task and tts_task and task.status:
            try:
                success = process_tts(session, tts_task, user_id=task.user_id)
                if success:
                    logger.info(f"Task {task_id} status updated to completed")
                    return True
                else:
                    logger.error(f"Task {task_id} failed during processing")
                    return False
            except Exception as e:
                session.rollback()
                logger.error(f"Error processing task {task_id}: {e}")
                return False
        else:
            logger.error(f"Task {task_id} is not pending or task not found")
            return False
    finally:
        session.remove()  # Dispose of the session correctly


@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def process_translation_task(self, task_id):
    session = make_session()
    try:
        task = session.query(Task).filter_by(id=task_id).one()
        translation_task = session.query(TranslationTask).filter_by(task_id=task_id).first()
        if task and translation_task:
            preprocess_audio_task.s(
                translation_task.input_filename,
                get_user_audio_directory(task.user_id),
                task.user_id,
                task_id
            ).apply_async(link=translate_segments.s(
                task_id,
                task.user_id,
                translation_task.model,
                translation_task.prompt,
                translation_task.response_format,
                translation_task.temperature,
                translation_task.input_filename,
                translation_task.original_filename
            ))
        else:
            logger.error(f"Task {task_id} is not pending or task not found")
    except Exception as e:
        logger.error(f"Error during translation processing for task_id={task_id}: {e}")
        socketio.emit("task_update", {"task_id": task_id, "status": "error", "error": str(e)}, room=str(task.user_id), namespace="/audio")
        raise self.retry(exc=e)
    finally:
        session.close()


@celery.task
def translate_segments(segment_filepaths, task_id, user_id, model, prompt, response_format, temperature, input_filename, original_filename):
    session = make_session()
    try:
        client, key_id, error = task_client(session, user_id)
        if error:
            raise Exception(error)

        translation_job = create_job(
            session,
            "translation",
            user_id,
            task_id,
            prompt,
            model,
            response_format,
            temperature,
            input_filename,
            original_filename,
        )

        segment_tasks = [
            translate_segment.s(
                segment_filepath,
                user_id,
                key_id,
                translation_job.id,
                model,
                prompt,
                response_format,
                temperature,
                index
            )
            for index, segment_filepath in enumerate(segment_filepaths)
        ]

        group_result = group(segment_tasks)()
        segment_details = group_result.get()

        aggregate_results.delay(segment_details, translation_job.id, task_id)

    except Exception as e:
        logger.error(f"Error during segment translation for task_id={task_id}: {e}")
        raise e
    finally:
        session.close()



@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def translate_segment(self, segment_filepath, user_id, api_key_id, job_id, model, prompt, response_format,
                       temperature, index):
    session = make_session()
    try:
        client, key_id, error = task_client(session, user_id)
        if error:
            raise Exception(error)

        with open(segment_filepath, "rb") as audio_file:
            result = client.audio.translations.create(
                    model=model,
                    file=audio_file,
                    prompt=prompt,
                    response_format=response_format,
                    temperature=temperature,
                )

        duration = get_audio_duration(segment_filepath)
        seconds = int(duration / 1000)
        segment_cost = whisper_cost(session=session, user_id=user_id, api_key_id=api_key_id, duration_seconds=seconds)

        create_translate_job_segment(session, job_id, result, index, duration)


        os.remove(segment_filepath)
        return duration, segment_cost

    except Exception as e:
            logger.error(f"Error during segment translation for job_id={job_id}: {e}")
            raise self.retry(exc=e)

@celery.task
def aggregate_results(results, job_id, task_id):
    session = make_session()
    try:
        task = session.query(Task).filter_by(id=task_id).one()
        translation_job = session.query(TranslationJob).filter_by(id=job_id).first()

        if task and translation_job:
            total_duration = sum(result[0] for result in results)
            total_cost = sum(result[1] for result in results)

            translation_job.finished = True
            translation_job.total_duration = total_duration
            translation_job.total_cost = total_cost
            session.commit()

            socketio.emit(
                "task_complete",
                {
                    "task_id": task_id,
                    "message": f"Translation processing for {translation_job.original_filename} completed!",
                    "status": "completed",
                    "job_type": "translation",
                    "job_details": {
                        "id": translation_job.id,
                        "model": translation_job.model,
                        "prompt": translation_job.prompt,
                        "response_format": translation_job.response_format,
                        "temperature": translation_job.temperature,
                        "original_filename": translation_job.original_filename,
                        "total_duration": total_duration,
                        "total_cost": total_cost,
                        "created_at": translation_job.created_at.isoformat(),
                    },
                },
                room=str(task.user_id),
                namespace="/audio",
            )
        else:
            logger.error(f"Task {task_id} not found or translation job not found")
    except Exception as e:
        logger.error(f"Error during result aggregation for task_id={task_id}: {e}")
    finally:
        session.close()

@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def process_transcription_task(self, task_id):
    session = make_session()
    try:
        task = session.query(Task).filter_by(id=task_id).one()
        transcription_task = session.query(TranscriptionTask).filter_by(task_id=task_id).first()
        if task and transcription_task:
            preprocess_audio_task.s(
                transcription_task.input_filename,
                get_user_audio_directory(task.user_id),
                task.user_id,
                task_id
            ).apply_async(link=transcribe_segments.s(
                task_id,
                task.user_id,
                transcription_task.model,
                transcription_task.language,
                transcription_task.prompt,
                transcription_task.response_format,
                transcription_task.temperature,
                transcription_task.input_filename,
                transcription_task.original_filename
            ))
        else:
            logger.error(f"Task {task_id} is not pending or task not found")
    except Exception as e:
        logger.error(f"Error during transcription processing for task_id={task_id}: {e}")
        socketio.emit("task_update", {"task_id": task_id, "status": "error", "error": str(e)}, room=str(task.user_id), namespace="/audio")
        raise self.retry(exc=e)
    finally:
        session.close()


@celery.task
def preprocess_audio_task(filepath, user_directory, user_id, task_id):
    try:
        socketio.emit(
            "task_progress",
            {"task_id": task_id, "message": "Starting audio file preprocessing..."},
            room=str(user_id),
            namespace="/audio",
        )
        file_size = os.path.getsize(filepath)
        if file_size > 50 * 1024 * 1024:  # 50 MB
            raise ValueError(f"File {filepath} is too large ({file_size} bytes) to process.")

        supported_formats = [".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm"]
        file_extension = Path(filepath).suffix.lower()
        if file_extension not in supported_formats:
            raise ValueError(f"Unsupported format: {file_extension}")

        audio, sample_rate = sf.read(filepath)

        start_trim = 0
        while start_trim < len(audio) and abs(audio[start_trim, 0]) < 0.01:
            start_trim += 1
        audio = audio[start_trim:]

        # Normalization
        max_amplitude = max(abs(audio[:, 0]))
        if max_amplitude > 0:
            audio = audio / max_amplitude

        # Split audio into chunks
        chunk_length = 10 * 60  # 10 minutes in seconds
        chunk_paths = []
        for i in range(0, len(audio), int(chunk_length * sample_rate)):
            chunk = audio[i:i + int(chunk_length * sample_rate)]
            chunk_filename = f"chunk_{task_id}_{i // int(chunk_length * sample_rate):03}.mp3"
            chunk_path = os.path.join(user_directory, chunk_filename)
            sf.write(chunk_path, chunk, sample_rate)
            chunk_paths.append(chunk_path)

        socketio.emit(
            "task_progress",
            {"task_id": task_id, "message": "Audio file preprocessing completed."},
            room=str(user_id),
            namespace="/audio",
        )

        return chunk_paths

    except Exception as e:
        socketio.emit(
            "task_progress",
            {"task_id": task_id, "message": f"Error during audio file preprocessing: {str(e)}"},
            room=str(user_id),
            namespace="/audio",
        )
        logger.error(f"Error during audio file preprocessing for task_id={task_id}: {e}")
        raise e


@celery.task
def transcribe_segments(segment_filepaths, task_id, user_id, model, language, prompt, response_format, temperature, input_filename, original_filename):
    session = make_session()
    try:
        client, key_id, error = task_client(session, user_id)
        if error:
            raise Exception(error)

        transcription_job = create_job(
            session,
            "transcription",
            user_id,
            task_id,
            prompt,
            model,
            response_format,
            temperature,
            input_filename,
            original_filename,
            language
        )

        segment_tasks = [
            transcribe_segment.s(
                segment_filepath,
                user_id,
                key_id,
                transcription_job.id,
                model,
                language,
                prompt,
                response_format,
                temperature,
                index
            )
            for index, segment_filepath in enumerate(segment_filepaths)
        ]

        group_result = group(segment_tasks)()
        segment_details = group_result.get()  # Ensure it's the list of results you need

        # Call aggregate_results after all segment tasks with actual results
        aggregate_results.delay(segment_details, transcription_job.id, task_id)

    except Exception as e:
        logger.error(f"Error during segment transcription for task_id={task_id}: {e}")
        raise e
    finally:
        session.close()



@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def transcribe_segment(self, segment_filepath, user_id, api_key_id, job_id, model, language, prompt, response_format,
                       temperature, index):
    session = make_session()
    try:
        client, key_id, error = task_client(session, user_id)
        if error:
            raise Exception(error)

        with open(segment_filepath, "rb") as audio_file:
            result = client.audio.transcriptions.create(
                    model=model,
                    file=audio_file,
                    language=language,
                    prompt=prompt,
                    response_format=response_format,
                    temperature=temperature,
                )

        duration = get_audio_duration(segment_filepath)
        seconds = int(duration / 1000)
        segment_cost = whisper_cost(session=session, user_id=user_id, api_key_id=api_key_id, duration_seconds=seconds)

        create_transcribe_job_segment(session, job_id, result, index, duration)


        os.remove(segment_filepath)
        return duration, segment_cost

    except Exception as e:
            logger.error(f"Error during segment transcription for job_id={job_id}: {e}")
            raise self.retry(exc=e)




@celery.task
def aggregate_results(results, job_id, task_id):
    session = make_session()
    try:
        task = session.query(Task).filter_by(id=task_id).one()
        transcription_job = session.query(TranscriptionJob).filter_by(id=job_id).first()

        if task and transcription_job:
            total_duration = sum(result[0] for result in results)
            total_cost = sum(result[1] for result in results)

            transcription_job.finished = True
            transcription_job.total_duration = total_duration
            transcription_job.total_cost = total_cost
            session.commit()

            socketio.emit(
                "task_complete",
                {
                    "task_id": task_id,
                    "message": f"Transcription processing for {transcription_job.original_filename} completed!",
                    "status": "completed",
                    "job_type": "transcription",
                    "job_details": {
                        "id": transcription_job.id,
                        "model": transcription_job.model,
                        "prompt": transcription_job.prompt,
                        "response_format": transcription_job.response_format,
                        "temperature": transcription_job.temperature,
                        "original_filename": transcription_job.original_filename,
                        "total_duration": total_duration,
                        "total_cost": total_cost,
                        "created_at": transcription_job.created_at.isoformat(),
                    },
                },
                room=str(task.user_id),
                namespace="/audio",
            )
        else:
            logger.error(f"Task {task_id} not found or transcription job not found")
    except Exception as e:
        logger.error(f"Error during result aggregation for task_id={task_id}: {e}")
    finally:
        session.close()