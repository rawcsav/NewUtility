import os

import openai
from flask_login import current_user
from pydub import AudioSegment

from app import db
from app.models.audio_models import (
    TTSPreferences,
    WhisperPreferences,
    TTSJob,
    TranscriptionJob,
    TranslationJob,
    TranscriptionJobSegment,
    TranslationJobSegment,
)
from app.utils.usage_util import num_tokens_from_string, chat_cost, tts_cost, whisper_cost
from config import appdir


def user_subdirectory(user_id):
    base_download_dir = os.path.join(appdir, "static", "user_files", "user_audio")
    user_subdirectory_path = os.path.join(base_download_dir, str(user_id))
    if not os.path.exists(user_subdirectory_path):
        os.makedirs(user_subdirectory_path)
    return user_subdirectory_path


def ms_until_sound(sound, silence_threshold_in_decibels=-20.0, chunk_size=10):
    trim_ms = 0

    assert chunk_size > 0, "Chunk size must be positive"

    while sound[trim_ms : trim_ms + chunk_size].dBFS < silence_threshold_in_decibels and trim_ms < len(sound):
        trim_ms += chunk_size

    return trim_ms


def find_nearest_silence(
    audio_segment, target_ms, search_radius_ms=20000, silence_thresh=-40, min_silence_len_ms=1000, seek_step_ms=100
):
    """
    Find the nearest point of silence within a specified radius around a target timestamp in an audio segment.
    """
    start_search_ms = max(0, target_ms - search_radius_ms)
    end_search_ms = min(len(audio_segment), target_ms + search_radius_ms)
    best_silence_start = target_ms  # Default to the target if no silence is found
    smallest_delta = search_radius_ms  # Initialize with the maximum possible delta

    for timestamp in range(start_search_ms, end_search_ms, seek_step_ms):
        if timestamp + min_silence_len_ms > len(audio_segment):
            break  # Avoid checking beyond the end of the audio_segment
        segment = audio_segment[timestamp : timestamp + min_silence_len_ms]
        if segment.dBFS < silence_thresh:
            delta = abs(timestamp - target_ms)
            if delta < smallest_delta:
                best_silence_start = timestamp
                smallest_delta = delta

    return best_silence_start


def export_audio_chunk(chunk, directory, filename, index):
    segment_filename = f"{filename}_segment_{index}.mp3"
    segment_filepath = os.path.join(directory, segment_filename)
    chunk.export(segment_filepath, format="mp3")
    return segment_filepath


def preprocess_audio(filepath, user_directory):
    max_size_in_bytes = 24 * 1024 * 1024
    supported_formats = ["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"]
    original_format = os.path.splitext(filepath)[-1].lower().strip(".")

    if original_format not in supported_formats:
        raise ValueError(f"Unsupported format: {original_format}")
    audio = AudioSegment.from_file(filepath, format=original_format)
    start_trim = ms_until_sound(audio)
    trimmed_audio = audio[start_trim:]
    new_filename = f"trim_{os.path.splitext(os.path.basename(filepath))[0]}.mp3"
    new_filepath = os.path.join(user_directory, new_filename)
    trimmed_audio.export(new_filepath, format="mp3")
    if os.path.getsize(new_filepath) <= max_size_in_bytes:
        os.remove(filepath)
        return [new_filepath]

    chunk_length_ms = 5 * 60 * 1000  # 5 minutes in milliseconds
    search_radius_ms = 20 * 1000  # 20 seconds in milliseconds
    chunks = []
    current_ms = 0
    while current_ms < len(trimmed_audio):
        next_split = find_nearest_silence(trimmed_audio, current_ms + chunk_length_ms, search_radius_ms)
        chunks.append(trimmed_audio[current_ms:next_split])
        current_ms = next_split
    segment_filepaths = [export_audio_chunk(chunk, user_directory, new_filepath, i) for i, chunk in enumerate(chunks)]
    os.remove(filepath)
    os.remove(new_filepath)
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


def determine_prompt(client, form_data):
    if "generate_prompt" in form_data and form_data["generate_prompt"]:
        generated_prompt = generate_prompt(session=db.session, client=client, instruction=form_data["generate_prompt"])
        return generated_prompt
    elif "prompt" in form_data and form_data["prompt"]:
        return form_data["prompt"]
    else:
        return ""


def generate_speech(
    session, client, api_key_id, user_id, model, voice, input_text, task_id, response_format="mp3", speed=1.0
):
    download_dir = user_subdirectory(user_id)
    tts_job = create_tts_job(session, user_id, model, voice, response_format, speed, input_text, task_id)
    tts_filename = f"{tts_job.id}.{response_format}"
    tts_filepath = os.path.join(download_dir, tts_filename)
    tts_job.output_filename = tts_filename
    session.commit()
    if not create_and_stream_tts_audio(client, model, voice, input_text, response_format, speed, tts_filepath):
        return {"error": "Failed to generate speech"}
    tts_cost(session=session, user_id=user_id, api_key_id=api_key_id, model_name=model, num_characters=len(input_text))
    return tts_filepath


def create_and_stream_tts_audio(client, model, voice, input_text, response_format, speed, filepath):
    try:
        response = client.audio.speech.create(
            model=model, voice=voice, input=input_text, response_format=response_format, speed=speed
        )
        response.stream_to_file(filepath)
        return True
    except openai.OpenAIError:
        return False


def process_audio_transcription(
    session,
    user_id,
    api_key_id,
    client,
    file_path,
    transcription_job,
    model,
    language,
    prompt,
    response_format,
    temperature,
    index,
    total_duration_ms=0,
):
    try:
        with open(file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model=model,
                file=audio_file,
                language=language,
                prompt=prompt,
                response_format=response_format,
                temperature=temperature,
            )
        if response_format in ["json", "verbose_json"]:
            transcript = transcript.model_dump_json()
        elif response_format in ["srt", "vtt"]:
            transcript = adjust_subtitle_timing(transcript, total_duration_ms, response_format)
        duration = get_audio_duration(file_path)
        seconds = duration * 1000
        whisper_cost(session=session, user_id=user_id, api_key_id=api_key_id, duration_seconds=seconds)
        create_transcription_job_segment(session, transcription_job.id, transcript, index, duration)
        return duration
    except openai.OpenAIError as e:
        return {"error": str(e)}


def transcribe_audio(
    session,
    user_id,
    api_key_id,
    client,
    file_paths,
    input_filename,
    response_format,
    temperature,
    task_id,
    model="whisper-1",
    language=None,
    prompt=None,
):
    transcription_job = create_transcription_job(
        session=session,
        user_id=user_id,
        prompt=prompt,
        model=model,
        language=language,
        response_format=response_format,
        temperature=temperature,
        input_filename=input_filename,
        task_id=task_id,
    )
    total_duration_ms = 0  # Initialize the total duration
    try:
        for index, file_path in enumerate(file_paths):
            segment_duration = process_audio_transcription(
                session,
                user_id,
                api_key_id,
                client,
                file_path,
                transcription_job,
                model,
                language,
                prompt,
                response_format,
                temperature,
                index,
                total_duration_ms,
            )
            if isinstance(segment_duration, dict):
                raise Exception(segment_duration["error"])
            total_duration_ms += segment_duration
        transcription_job.finished = True
        session.commit()
    except Exception as e:
        session.rollback()
    return transcription_job.id


def process_audio_translation(
    session,
    user_id,
    api_key_id,
    client,
    file_path,
    translation_job,
    model,
    prompt,
    response_format,
    temperature,
    index,
    total_duration_ms=0,
):
    try:
        with open(file_path, "rb") as audio_file:
            translation = client.audio.translations.create(
                model=model, file=audio_file, prompt=prompt, response_format=response_format, temperature=temperature
            )
            if response_format in ["json", "verbose_json"]:
                translation = translation.model_dump_json()
            elif response_format in ["srt", "vtt"]:
                transcript = adjust_subtitle_timing(translation, total_duration_ms, response_format)
            duration = get_audio_duration(file_path)
            seconds = duration * 1000
            whisper_cost(session=session, user_id=user_id, api_key_id=api_key_id, duration_seconds=seconds)
            create_translation_job_segment(session, translation_job.id, transcript, index, duration)
            return duration
    except openai.OpenAIError as e:
        return {"error": str(e)}


def translate_audio(
    session,
    api_key_id,
    user_id,
    client,
    file_paths,
    input_filename,
    task_id,
    model="whisper-1",
    prompt=None,
    response_format="text",
    temperature=0.0,
):
    translation_job = create_translation_job(
        session=session,
        user_id=user_id,
        task_id=task_id,
        prompt=prompt,
        model=model,
        response_format=response_format,
        temperature=temperature,
        input_filename=input_filename,
    )
    total_duration_ms = 0
    try:
        for index, file_path in enumerate(file_paths):
            segment_duration = process_audio_transcription(
                session,
                api_key_id,
                user_id,
                client,
                file_path,
                translation_job,
                model,
                prompt,
                response_format,
                temperature,
                index,
                total_duration_ms,
            )
            if isinstance(segment_duration, dict):
                raise Exception(segment_duration["error"])
            total_duration_ms += segment_duration
        translation_job.finished = True
        session.commit()
    except Exception as e:
        session.rollback()
    return translation_job.id


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


def create_transcription_job(
    session, user_id, prompt, model, language, response_format, temperature, task_id, input_filename
):
    job = TranscriptionJob(
        user_id=user_id,
        task_id=task_id,
        prompt=prompt,
        model=model,
        language=language,
        response_format=response_format,
        temperature=temperature,
        input_filename=input_filename,
    )
    session.add(job)
    session.commit()
    return job


def create_translation_job(session, user_id, prompt, model, response_format, temperature, task_id, input_filename):
    job = TranslationJob(
        user_id=user_id,
        task_id=task_id,
        prompt=prompt,
        model=model,
        response_format=response_format,
        temperature=temperature,
        input_filename=input_filename,
    )
    session.add(job)
    session.commit()
    return job


def create_transcription_job_segment(session, transcription_job_id, transcription, job_index, duration):
    segment = TranscriptionJobSegment(
        transcription_job_id=transcription_job_id, output_content=transcription, job_index=job_index, duration=duration
    )
    session.add(segment)
    session.commit()
    return segment


def create_translation_job_segment(session, translation_job_id, translation, job_index, duration):
    segment = TranslationJobSegment(
        translation_job_id=translation_job_id, output_content=translation, job_index=job_index, duration=duration
    )
    session.add(segment)
    session.commit()
    return segment


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

    # Define the file path
    file_name = f"{job_id}.{file_extension}"
    file_path = os.path.join(user_directory, file_name)

    # Write content to the file
    with open(file_path, "wb") as file:
        file.write(content.encode("utf-8"))

    return file_path
