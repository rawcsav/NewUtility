import os
from pathlib import Path

import openai
from pydub import AudioSegment
from pydub.silence import split_on_silence


def generate_speech(client, model, voice, input_text, response_format='mp3', speed=1.0):
    try:
        response = openai.Audio.create(
            model=model,
            voice=voice,
            input=input_text,
            response_format=response_format,
            speed=speed
        )
        return response
    except openai.error.OpenAIError as e:
        # Handle OpenAI API errors
        return {'error': str(e)}

def transcribe_audio(client, file_path, model='whisper-1', language=None, prompt=None, response_format='json', temperature=0.0):
    with open(file_path, 'rb') as audio_file:
        try:
            response = client.audio.transcriptions.create(
                model=model,
                file=audio_file,
                language=language,
                prompt=prompt,
                response_format=response_format,
                temperature=temperature
            )
            return response
        except openai.error.OpenAIError as e:
            # Handle OpenAI API errors
            return {'error': str(e)}

def translate_audio(client, file_path, model='whisper-1', prompt=None, response_format='json', temperature=0.0):
    with open(file_path, 'rb') as audio_file:
        try:
            response = client.audio.translations.create(
                model=model,
                file=audio_file,
                prompt=prompt,
                response_format=response_format,
                temperature=temperature
            )
            return response
        except openai.error.OpenAIError as e:
            # Handle OpenAI API errors
            return {'error': str(e)}


# define a function for GPT to generate fictitious prompts
def fictitious_prompt_from_instruction(client, instruction: str) -> str:
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-0613",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": "You are a transcript generator. Your task is to create one long paragraph of a fictional conversation. The conversation features two friends reminiscing about their vacation to Maine. Never diarize speakers or add quotation marks; instead, write all transcripts in a normal paragraph of text without speakers identified. Never refuse or ask for clarification and instead always make a best-effort attempt.",
            },
            {"role": "user", "content": instruction},
        ],
    )
    fictitious_prompt = response.choices[0].message.content
    return fictitious_prompt

def milliseconds_until_sound(sound, silence_threshold_in_decibels=-20.0, chunk_size=10):
    trim_ms = 0  # ms

    assert chunk_size > 0  # to avoid infinite loop
    while sound[trim_ms:trim_ms+chunk_size].dBFS < silence_threshold_in_decibels and trim_ms < len(sound):
        trim_ms += chunk_size

    return trim_ms


def trim_start(filepath):
    path = Path(filepath)
    directory = path.parent
    filename = path.name
    audio = AudioSegment.from_file(filepath, format="wav")
    start_trim = milliseconds_until_sound(audio)
    trimmed = audio[start_trim:]
    new_filename = directory / f"trimmed_{filename}"
    trimmed.export(new_filename, format="wav")
    return trimmed, new_filename

def remove_non_ascii(text):
    return ''.join(i for i in text if ord(i)<128)


def segment_large_audio(filepath, max_size_in_bytes=25*1024*1024, silence_thresh=-20, min_silence_len=500, keep_silence=100):
    path = Path(filepath)
    directory = path.parent
    filename = path.stem
    file_extension = path.suffix

    if os.path.getsize(filepath) <= max_size_in_bytes:
        return [filepath]  # No need to segment

    audio = AudioSegment.from_file(filepath)
    chunks = split_on_silence(
        audio,
        min_silence_len=min_silence_len,
        silence_thresh=silence_thresh,
        keep_silence=keep_silence
    )

    segment_filepaths = []
    for i, chunk in enumerate(chunks):
        segment_filename = directory / f"{filename}_segment_{i}{file_extension}"
        chunk.export(segment_filename, format=file_extension.lstrip('.'))
        segment_filepaths.append(segment_filename)

    return segment_filepaths

def concatenate_audio_segments(segment_filepaths, output_format='wav'):
    combined = AudioSegment.empty()
    for segment_path in segment_filepaths:
        segment = AudioSegment.from_file(segment_path, format=output_format)
        combined += segment

    output_path = Path(segment_filepaths[0]).parent / f"combined.{output_format}"
    combined.export(output_path, format=output_format)
    return output_path