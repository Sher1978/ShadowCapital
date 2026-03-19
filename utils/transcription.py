import os
import logging
from config import OPENAI_API_KEY, GEMINI_API_KEY

async def transcribe_voice(file_path: str) -> str:
    """
    Transcribes audio file using Gemini 1.5 Flash (primary) or OpenAI Whisper (fallback).
    """
    # Lazy imports to speed up bot startup
    import google.generativeai as genai
    from openai import AsyncOpenAI
    
    client_openai = AsyncOpenAI(api_key=OPENAI_API_KEY)
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)

    # 1. Try Gemini 1.5 Flash (Very cheap/fast)
    if GEMINI_API_KEY:
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            # Upload file to Gemini
            sample_file = genai.upload_file(path=file_path)
            response = model.generate_content([sample_file, "Расшифруй это аудио сообщение в текст СТРОГО без своих комментариев."])
            if response.text:
                return response.text
        except Exception as e:
            logging.warning(f"Gemini transcription failed, falling back to Whisper: {e}")

    # 2. Try OpenAI Whisper (Fallback)
    if OPENAI_API_KEY:
        try:
            with open(file_path, "rb") as audio_file:
                transcript = await client_openai.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )
            return transcript
        except Exception as e:
            logging.error(f"Whisper transcription error: {e}")
            return f"Error: Transcription failed ({e})"
    
    return "Error: No AI keys available for transcription"
