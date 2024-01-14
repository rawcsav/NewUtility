import json
import os
import re
from datetime import timedelta

import openai
from flask import current_app
from flask_login import current_user
from pydub import AudioSegment
from pydub.silence import split_on_silence

from app import db
from app.database import (
    generate_uuid,
    TranscriptionJobSegment,
    TranslationJobSegment,
    TranslationJob,
    TranscriptionJob,
    TTSJob,
    TTSPreferences,
    WhisperPreferences,
)


def user_subdirectory(user_id):
    base_download_dir = current_app.config["USER_AUDIO_DIRECTORY"]

    user_subdirectory_path = os.path.join(base_download_dir, str(user_id))

    if not os.path.exists(user_subdirectory_path):
        os.makedirs(user_subdirectory_path)

    return user_subdirectory_path


def convert_format(filepath, target_format="mp3"):
    supported_formats = ["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"]
    if target_format not in supported_formats:
        raise ValueError(f"Unsupported target format: {target_format}")

    original_format = os.path.splitext(filepath)[-1].lower().strip(".")
    if original_format not in supported_formats:
        raise ValueError(f"Unsupported original format: {original_format}")

    if original_format == target_format:
        return filepath

    audio = AudioSegment.from_file(filepath, format=original_format)
    new_filepath = os.path.splitext(filepath)[0] + "." + target_format
    audio.export(new_filepath, format=target_format)

    os.remove(filepath)

    return new_filepath


# Function to find the first sound in an audio file after a period of silence
def ms_until_sound(sound, silence_threshold_in_decibels=-20.0, chunk_size=10):
    """Find the number of milliseconds until sound is detected in an audio segment."""
    trim_ms = 0  # Start at the beginning of the audio segment

    assert chunk_size > 0, "Chunk size must be positive"

    # Iterate over chunks of the audio segment until sound is detected
    while sound[
        trim_ms : trim_ms + chunk_size
    ].dBFS < silence_threshold_in_decibels and trim_ms < len(sound):
        trim_ms += chunk_size

    return trim_ms


def trim_start(filepath):
    directory, filename = os.path.split(filepath)
    basename, ext = os.path.splitext(filename)
    audio = AudioSegment.from_file(filepath, format="mp3")
    start_trim = ms_until_sound(audio)
    trimmed_audio = audio[start_trim:]
    new_filename = os.path.join(directory, f"trimmed_{basename}{ext}")
    trimmed_audio.export(new_filename, format="mp3")
    return new_filename


# Utility function to export an audio chunk
def export_audio_chunk(chunk, directory, filename, file_extension, index):
    """Export a single audio chunk to a file."""
    segment_filename = f"{filename}_segment_{index}{file_extension}"
    segment_filepath = os.path.join(directory, segment_filename)
    chunk.export(segment_filepath, format=file_extension.lstrip("."))
    return segment_filepath


# Refactored segment_audio function with extracted export logic
def segment_audio(
    filepath,
    max_size_in_bytes=25 * 1024 * 1024,
    silence_thresh=-20,
    min_silence_len=500,
    keep_silence=100,
):
    """Segment an audio file into smaller chunks based on silence detection."""
    directory, filename_with_extension = os.path.split(filepath)
    filename, file_extension = os.path.splitext(filename_with_extension)

    if os.path.getsize(filepath) <= max_size_in_bytes:
        return [filepath]

    audio = AudioSegment.from_file(filepath)
    chunks = split_on_silence(
        audio,
        min_silence_len=min_silence_len,
        silence_thresh=silence_thresh,
        keep_silence=keep_silence,
    )

    segment_filepaths = [
        export_audio_chunk(chunk, directory, filename, file_extension, i)
        for i, chunk in enumerate(chunks)
    ]

    return segment_filepaths


def generate_prompt(client, instruction: str) -> str:
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
    return fictitious_prompt


def determine_prompt(client, form_data):
    if form_data.generate_prompt:
        generated_prompt = generate_prompt(client, form_data.generate_prompt)
        return generated_prompt
    elif form_data.prompt:
        return form_data.prompt
    else:
        return ""


def remove_non_ascii(text):
    return "".join(i for i in text if ord(i) < 128)


def generate_speech(client, model, voice, input_text, response_format="mp3", speed=1.0):
    download_dir = user_subdirectory(current_user.id)
    tts_job = create_tts_job(
        current_user.id, model, voice, response_format, speed, input_text
    )
    tts_filename = f"tts_{tts_job.id}.{response_format}"
    tts_filepath = os.path.join(download_dir, tts_filename)

    if not create_and_stream_tts_audio(
        client, model, voice, input_text, response_format, speed, tts_filepath
    ):
        return {"error": "Failed to generate speech"}

    return tts_filepath, tts_filename


def create_and_stream_tts_audio(
    client, model, voice, input_text, response_format, speed, filepath
):
    try:
        response = client.audio.speech.create(
            model=model,
            voice=voice,
            input=input_text,
            response_format=response_format,
            speed=speed,
        )
        response.stream_to_file(filepath)
        return True
    except openai.OpenAIError:
        return False


def process_audio_transcription(
    client,
    file_path,
    transcription_job,
    model,
    language,
    prompt,
    response_format,
    temperature,
    index,
):
    try:
        with open(file_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model=model,
                file=audio_file,
                language=language,
                prompt=prompt,
                response_format=response_format,
                temperature=temperature,
            )
        transcript = remove_non_ascii(response)
        transcript_filename = (
            f"transcript_{transcription_job.id}_{index}.{response_format}"
        )
        transcript_filepath = os.path.join(
            user_subdirectory(transcription_job.user_id), transcript_filename
        )
        with open(transcript_filepath, "w", encoding="utf-8") as outfile:
            outfile.write(transcript)
        create_transcription_job_segment(
            transcription_job.id, file_path, transcript_filepath, index
        )
        return transcript_filepath
    except openai.OpenAIError as e:
        return {"error": str(e)}


def transcribe_audio(
    client,
    file_paths,
    model="whisper-1",
    language=None,
    prompt=None,
    response_format="text",
    temperature=0.0,
):
    transcription_job = create_transcription_job(
        user_id=current_user.id,
        prompt=prompt,
        model=model,
        language=language,
        response_format=response_format,
        temperature=temperature,
    )
    transcript_file_paths = []
    for index, file_path in enumerate(file_paths):
        result = process_audio_transcription(
            client,
            file_path,
            transcription_job,
            model,
            language,
            prompt,
            response_format,
            temperature,
            index,
        )
        if "error" in result:
            return result
        transcript_file_paths.append(result)

    output_filename = f"transcript_{transcription_job.id}.{response_format}"
    output_filepath = os.path.join(user_subdirectory(current_user.id), output_filename)
    concatenate_transcripts(transcript_file_paths, response_format, output_filepath)
    transcription_job.final_output_path = output_filepath
    db.session.commit()
    return output_filepath


def process_audio_translation(
    client,
    file_path,
    translation_job,
    model,
    prompt,
    response_format,
    temperature,
    index,
):
    try:
        with open(file_path, "rb") as audio_file:
            response = client.audio.translations.create(
                model=model,
                file=audio_file,
                prompt=prompt,
                response_format=response_format,
                temperature=temperature,
            )
        translation = remove_non_ascii(response)
        translation_filename = (
            f"translation_{translation_job.id}_{index}.{response_format}"
        )
        translation_filepath = os.path.join(
            user_subdirectory(translation_job.user_id), translation_filename
        )
        with open(translation_filepath, "w", encoding="utf-8") as outfile:
            outfile.write(translation)
        create_translation_job_segment(
            translation_job.id, file_path, translation_filepath, index
        )
        return translation_filepath
    except openai.OpenAIError as e:
        return {"error": str(e)}


def translate_audio(
    client,
    file_paths,
    model="whisper-1",
    prompt=None,
    response_format="text",
    temperature=0.0,
):
    translation_job = create_translation_job(
        user_id=current_user.id,
        prompt=prompt,
        model=model,
        response_format=response_format,
        temperature=temperature,
    )
    translation_file_paths = []
    for index, file_path in enumerate(file_paths):
        result = process_audio_translation(
            client,
            file_path,
            translation_job,
            model,
            prompt,
            response_format,
            temperature,
            index,
        )
        if "error" in result:
            return result
        translation_file_paths.append(result)

    output_filename = f"translation_{translation_job.id}.{response_format}"
    output_filepath = os.path.join(user_subdirectory(current_user.id), output_filename)
    concatenate_transcripts(translation_file_paths, response_format, output_filepath)
    translation_job.final_output_path = output_filepath
    db.session.commit()
    return output_filename


def concatenate_transcripts(transcript_filepaths, output_format, output_filepath):
    if output_format in ["srt", "vtt"]:
        return concatenate_subtitles(transcript_filepaths, output_filepath)
    else:
        concatenated_transcript = []

        for filepath in transcript_filepaths:
            with open(filepath, "r", encoding="utf-8") as file:
                if output_format in ["json", "verbose_json"]:
                    transcript_data = json.load(file)
                    concatenated_transcript.extend(transcript_data["transcript"])
                elif output_format == "text":
                    transcript_data = file.read()
                    concatenated_transcript.append(transcript_data)
        with open(output_filepath, "w", encoding="utf-8") as outfile:
            if output_format in ["json", "verbose_json"]:
                json.dump(
                    {"transcript": concatenated_transcript},
                    outfile,
                    ensure_ascii=False,
                    indent=4,
                )
            elif output_format == "text":
                outfile.write("\n".join(concatenated_transcript))

        return output_filepath


def parse_subs(subtitle_content, file_format):
    if file_format == "srt":
        pattern = re.compile(
            r"(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) "
            r"--> (\d{2}:\d{2}:\d{2},\d{3})\n(.*?)\n\n",
            re.DOTALL,
        )
    elif file_format == "vtt":
        pattern = re.compile(
            r"(\d+)\n(\d{2}:\d{2}:\d{2}\.\d{3}) "
            r"--> (\d{2}:\d{2}:\d{2}\.\d{3})\n(.*?)\n\n",
            re.DOTALL,
        )
    else:
        return []

    matches = pattern.findall(subtitle_content)
    return [
        {"index": int(index), "start": start, "end": end, "text": text.strip()}
        for index, start, end, text in matches
    ]


def time_calc_subs(time_str):
    time_parts = re.split("[.,:]", time_str)
    return timedelta(
        hours=int(time_parts[0]),
        minutes=int(time_parts[1]),
        seconds=int(time_parts[2]),
        milliseconds=int(time_parts[3]),
    )


def adjust_timestamps(subtitles, delta):
    for subtitle in subtitles:
        start_td = time_calc_subs(subtitle["start"]) + delta
        end_td = time_calc_subs(subtitle["end"]) + delta
        subtitle["start"] = str(start_td)[:-3].replace(".", ",")
        subtitle["end"] = str(end_td)[:-3].replace(".", ",")


def subs_string(subtitles, file_format):
    if file_format == "srt":
        return "\n\n".join(
            f"{i+1}\n{sub['start'].replace('.', ',')} "
            f"--> {sub['end'].replace('.', ',')}\n{sub['text']}"
            for i, sub in enumerate(subtitles)
        )
    elif file_format == "vtt":
        return "\n\n".join(
            f"{i+1}\n{sub['start']} --> {sub['end']}\n{sub['text']}"
            for i, sub in enumerate(subtitles)
        )


def detect_format(subtitle_content):
    if "WEBVTT" in subtitle_content:
        return "vtt"
    else:
        return "srt"


def concatenate_subtitles(subtitle_filepaths, output_filepath):
    concatenated_subtitles = []
    total_delta = timedelta(0)

    for filepath in subtitle_filepaths:
        with open(filepath, "r", encoding="utf-8") as file:
            content = file.read()
            file_format = detect_format(content)
            subtitles = parse_subs(content, file_format)
            if concatenated_subtitles:
                last_subtitle = concatenated_subtitles[-1]
                total_delta += time_calc_subs(last_subtitle["end"])
            adjust_timestamps(subtitles, total_delta)
            concatenated_subtitles.extend(subtitles)

    output_format = detect_format(concatenated_subtitles[0]["text"])
    with open(output_filepath, "w", encoding="utf-8") as outfile:
        outfile.write(subs_string(concatenated_subtitles, output_format))


def create_tts_job(
    user_id, model, voice, response_format, speed, input_text, final_output_path=None
):
    uuid = str(generate_uuid())
    job = TTSJob(
        id=uuid,
        user_id=user_id,
        model=model,
        voice=voice,
        response_format=response_format,
        speed=speed,
        input_text=input_text,
        final_output_path=final_output_path,
    )
    db.session.add(job)
    db.session.commit()
    return job


def create_transcription_job(
    user_id,
    prompt,
    model,
    language,
    response_format,
    temperature,
    final_output_path=None,
):
    uuid = str(generate_uuid())

    job = TranscriptionJob(
        id=uuid,
        user_id=user_id,
        prompt=prompt,
        model=model,
        language=language,
        response_format=response_format,
        temperature=temperature,
        final_output_path=final_output_path,
    )
    db.session.add(job)
    db.session.commit()
    return job


def create_translation_job(
    user_id, prompt, model, response_format, temperature, final_output_path=None
):
    uuid = str(generate_uuid())
    job = TranslationJob(
        id=uuid,
        user_id=user_id,
        prompt=prompt,
        model=model,
        response_format=response_format,
        temperature=temperature,
        final_output_path=final_output_path,
    )
    db.session.add(job)
    db.session.commit()
    return job


def create_transcription_job_segment(
    transcription_job_id, input_file_path, output_file_path, job_index
):
    uuid = str(generate_uuid())
    segment = TranscriptionJobSegment(
        id=uuid,
        transcription_job_id=transcription_job_id,
        input_file_path=input_file_path,
        output_file_path=output_file_path,
        job_index=job_index,
    )
    db.session.add(segment)
    db.session.commit()
    return segment


def create_translation_job_segment(
    translation_job_id, input_file_path, output_file_path, job_index
):
    uuid = str(generate_uuid())

    segment = TranslationJobSegment(
        id=uuid,
        translation_job_id=translation_job_id,
        input_file_path=input_file_path,
        output_file_path=output_file_path,
        job_index=job_index,
    )
    db.session.add(segment)
    db.session.commit()
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
        return {
            "model": "tts-1",
            "voice": "alloy",
            "response_format": "mp3",
            "speed": "1.0",
        }


def get_whisper_preferences(user_id):
    preferences = WhisperPreferences.query.filter_by(user_id=user_id).first()
    if preferences:
        return {
            "model": preferences.model,
            "language": preferences.language,
            "response_format": preferences.response_format,
        }
    else:
        return {
            "model": "whisper-1",
            "language": "en",
            "response_format": "text",
        }
