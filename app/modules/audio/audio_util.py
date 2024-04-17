import os
from pathlib import Path

import openai
from flask_login import current_user
from pydub import AudioSegment
from app.modules.user.user_util import get_user_audio_directory
from app import db, socketio
from app.models.audio_models import (
    TTSPreferences,
    WhisperPreferences,
    TTSJob,
    TranscriptionJob,
    TranslationJob, TranscriptionJobSegment, TranslationJobSegment,
)
from app.utils.usage_util import num_tokens_from_string, chat_cost, tts_cost
from app.utils.logging_util import configure_logging

logger = configure_logging()


def ms_until_sound(sound, silence_threshold_in_decibels=-20.0, chunk_size=10):
    trim_ms = 0

    assert chunk_size > 0
    while sound[trim_ms:trim_ms+chunk_size].dBFS < silence_threshold_in_decibels and trim_ms < len(sound):
        trim_ms += chunk_size

    return trim_ms


def trim_start(filepath, original_format, target_format='mp3', target_bitrate='64k', sample_rate=22050):
    silence_threshold_in_decibels = -20.0
    path = Path(filepath)
    directory = path.parent
    filename = path.stem


    start_trim = 0
    chunk_size = 10 * 1000
    with open(filepath, 'rb') as f:
        audio_chunk = AudioSegment.from_file(f, format=original_format, start_second=0, duration=chunk_size / 1000)
        while audio_chunk.dBFS < silence_threshold_in_decibels and start_trim < len(audio_chunk):
            start_trim += chunk_size
            f.seek(0)  # Reset file pointer to the beginning for each new chunk
            audio_chunk = AudioSegment.from_file(f, format=original_format, start_second=start_trim / 1000,
                                                 duration=chunk_size / 1000)

    audio = AudioSegment.from_file(filepath, format=original_format)[start_trim:]
    audio = audio.set_frame_rate(sample_rate)
    new_filename = directory / f"trim_{filename}.{target_format}"
    audio.export(new_filename, bitrate=target_bitrate, format=target_format)
    os.remove(filepath)
    return audio, new_filename

def find_nearest_silence(
    audio_segment, target_ms, search_radius_ms=20000, silence_thresh=-40, min_silence_len_ms=1000, seek_step_ms=100
):
    start_search_ms = max(0, target_ms - search_radius_ms)
    end_search_ms = min(len(audio_segment), target_ms + search_radius_ms)
    best_silence_start = target_ms
    smallest_delta = search_radius_ms

    for timestamp in range(start_search_ms, end_search_ms, seek_step_ms):
        if timestamp + min_silence_len_ms > len(audio_segment):
            break
        segment = audio_segment[timestamp: timestamp + min_silence_len_ms]
        if segment.dBFS < silence_thresh:
            delta = abs(timestamp - target_ms)
            if delta < smallest_delta:
                best_silence_start = timestamp
                smallest_delta = delta
    logger.info(f"Nearest silence found at {best_silence_start} ms.")
    return best_silence_start


def process_and_export_segment(chunk, chunk_filepath, segment_index):
    logger.info(f"Exporting segment {segment_index}: {chunk_filepath}")
    chunk.export(chunk_filepath, format="mp3")
    return chunk_filepath


def split_and_export_chunks(audio, filepath, user_directory, user_id, task_id):
    logger.info("Splitting and exporting audio segments...")
    chunk_length_ms = 10 * 60 * 1000  # 5 minutes in milliseconds
    search_radius_ms = 20 * 1000  # 20 seconds in milliseconds
    current_ms = 0
    segment_filepaths = []

    while current_ms < len(audio):
        next_split = find_nearest_silence(audio, current_ms + chunk_length_ms, search_radius_ms)
        if next_split == -1 or next_split >= len(audio):
            next_split = len(audio)

        # Load only the required chunk into memory
        chunk = audio[current_ms:next_split]
        current_ms = next_split

        segment_index = len(segment_filepaths)
        original_path = Path(filepath)
        chunk_filename = f"chunk_{segment_index:03}_{original_path.stem}.mp3"
        chunk_filepath = os.path.join(user_directory, chunk_filename)

        # Process and export the chunk
        process_and_export_segment(chunk, chunk_filepath, segment_index)
        segment_filepaths.append(chunk_filepath)

        # Free up memory by removing the processed chunk
        chunk.clear()

    logger.info("All segments exported.")
    return segment_filepaths




def parse_timestamp(timestamp):
    hours, minutes, seconds = timestamp.split(":")
    seconds, milliseconds = seconds.split(",")
    return (int(hours) * 3600 + int(minutes) * 60 + int(seconds)) * 1000 + int(milliseconds)


def format_timestamp(milliseconds):
    hours = milliseconds // 3600000
    milliseconds %= 3600000
    minutes = milliseconds // 60000
    milliseconds %= 60000
    seconds = milliseconds // 1000
    milliseconds %= 1000
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


def adjust_subtitle_timing(subtitle_content, previous_duration_ms, response_format):
    if response_format.lower() not in ["srt", "vtt"] or previous_duration_ms == 0:
        return subtitle_content

    adjusted_subtitle = []
    for line in subtitle_content.splitlines():
        if "-->" in line:
            start, end = line.split(" --> ")
            start_ms = parse_timestamp(start) + previous_duration_ms
            end_ms = parse_timestamp(end) + previous_duration_ms
            adjusted_subtitle.append(f"{format_timestamp(start_ms)} --> {format_timestamp(end_ms)}")
        else:
            adjusted_subtitle.append(line)
    return "\n".join(adjusted_subtitle)


def get_audio_duration(file_path):
    audio = AudioSegment.from_file(file_path)
    return len(audio)


def generate_prompt(session, client, instruction: str) -> str:
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-0613",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": "You are a transcript generator. Your task is to "
                "create one long paragraph of a fictional conversation. "
                "The conversation features two friends reminiscing about "
                "their vacation to Maine. Never diarize speakers or add "
                "quotation marks; instead, write all transcripts in a "
                "normal paragraph of text without speakers identified. "
                "Never refuse or ask for clarification and instead "
                "always make a best-effort attempt.",
            },
            {"role": "user", "content": instruction},
        ],
    )

    fictitious_prompt = response.choices[0].message.content
    total_prompt_tokens = num_tokens_from_string(instruction, "gpt-3.5-turbo-0613")
    total_completion_tokens = num_tokens_from_string(fictitious_prompt, "gpt-3.5-turbo-0613")
    chat_cost(
        session=session,
        user_id=current_user.id,
        api_key_id=current_user.selected_api_key_id,
        model="gpt-3.5-turbo-0613",
        input_tokens=total_prompt_tokens,
        completion_tokens=total_completion_tokens,
    )
    return fictitious_prompt


def determine_prompt(client, form_data, task_id, user_id):
    if "generate_prompt" in form_data and form_data["generate_prompt"]:
        socketio.emit(
            "task_progress",
            {"task_id": task_id, "message": "Generating prompt..."},
            room=str(user_id),
            namespace="/audio",
        )
        generated_prompt = generate_prompt(session=db.session, client=client, instruction=form_data["generate_prompt"])
        return generated_prompt
    elif "prompt" in form_data and form_data["prompt"]:
        return form_data["prompt"]
    else:
        return ""


def generate_speech(
    session, client, api_key_id, user_id, model, voice, input_text, task_id, response_format="mp3", speed=1.0
):
    download_dir = get_user_audio_directory(user_id)
    tts_job = create_tts_job(session, user_id, model, voice, response_format, speed, input_text, task_id)
    tts_filename = f"{tts_job.id}.{response_format}"
    tts_filepath = os.path.join(download_dir, tts_filename)
    tts_job.output_filename = tts_filename
    session.commit()
    if not create_and_stream_tts_audio(client, model, voice, input_text, response_format, speed, tts_filepath):
        return {"error": "Failed to generate speech"}
    socketio.emit(
        "task_progress",
        {"task_id": task_id, "message": "Calculating TTS cost..."},
        room=str(user_id),
        namespace="/audio",
    )
    tts_cost(session=session, user_id=user_id, api_key_id=api_key_id, model_name=model, num_characters=len(input_text))
    return tts_filepath, tts_job.id


def create_and_stream_tts_audio(client, model, voice, input_text, response_format, speed, filepath):
    try:
        response = client.audio.speech.create(
            model=model, voice=voice, input=input_text, response_format=response_format, speed=speed
        )
        response.stream_to_file(filepath)
        return True
    except openai.OpenAIError:
        return False








def create_tts_job(session, user_id, model, voice, response_format, speed, input_text, task_id, output_filename=None):
    job = TTSJob(
        user_id=user_id,
        task_id=task_id,
        model=model,
        voice=voice,
        response_format=response_format,
        speed=speed,
        input_text=input_text,
        output_filename=output_filename,
    )
    session.add(job)
    session.commit()
    return job


def create_job(session, job_type, user_id, task_id, prompt, model, response_format, temperature, input_filename,
               original_filename, language=None):
    # Map job_type strings to the corresponding SQLAlchemy model classes
    job_type_map = {
        "transcription": TranscriptionJob,
        "translation": TranslationJob,
    }

    job_model = job_type_map.get(job_type)
    if not job_model:
        raise ValueError(f"Invalid job type: {job_type}")

    # Prepare the job details
    job_kwargs = {
        "user_id": user_id,
        "task_id": task_id,
        "prompt": prompt,
        "model": model,
        "response_format": response_format,
        "temperature": temperature,
        "input_filename": input_filename,
        "original_filename": original_filename,
    }

    # Add language to the job parameters if it's provided
    if language is not None:
        job_kwargs["language"] = language

    # Create and add the job to the session using the dynamically selected model
    job = job_model(**job_kwargs)
    session.add(job)
    session.commit()

    return job




def get_tts_preferences(user_id):
    preferences = TTSPreferences.query.filter_by(user_id=user_id).first()

    if preferences:
        return {
            "model": preferences.model,
            "voice": preferences.voice,
            "response_format": preferences.response_format,
            "speed": preferences.speed,
        }
    else:
        return {"model": "tts-1", "voice": "alloy", "response_format": "mp3", "speed": "1.0"}


def get_whisper_preferences(user_id):
    preferences = WhisperPreferences.query.filter_by(user_id=user_id).first()
    if preferences:
        return {
            "model": preferences.model,
            "language": preferences.language,
            "response_format": preferences.response_format,
            "temperature": preferences.temperature,
        }
    else:
        return {"model": "whisper-1", "language": "en", "response_format": "text", "temperature": "0.0"}


def save_file_to_disk(content, file_extension, job_id, user_directory):
    if not os.path.exists(user_directory):
        os.makedirs(user_directory)

    file_name = f"{job_id}.{file_extension}"
    file_path = os.path.join(user_directory, file_name)

    with open(file_path, "wb") as file:
        file.write(content.encode("utf-8"))

    return file_path



def create_transcribe_job_segment(session, job_id: int, content: str, index: int, duration: int):
    try:
        segment = TranscriptionJobSegment(
            transcription_job_id=job_id,
            output_content=content,
            job_index=index,
            duration=duration,
        )
        session.add(segment)
        session.commit()
        return segment
    except Exception as e:
        session.rollback()
        raise e


def create_translate_job_segment(session, job_id: int, content: str, index: int, duration: int):
    try:
        segment = TranslationJobSegment(
            translation_job_id=job_id,
            output_content=content,
            job_index=index,
            duration=duration,
        )
        session.add(segment)
        session.commit()
        return segment
    except Exception as e:
        session.rollback()
        raise e