from typing import Literal
from openai import OpenAI

import os
from dotenv import load_dotenv

load_dotenv()

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def call_speech_generator(input_text:str, output_file_name:str,
                                selected_voice:Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"]="shimmer",
                                 output_file_directory:str="./_outputs/speech"):

    generated_speech_file_path = f"{output_file_directory}/{output_file_name}.mp3"

    AI_Response = openai_client.audio.speech.create(
        model="tts-1-hd",
        voice=selected_voice,
        input= input_text
    )

    AI_Response.stream_to_file(generated_speech_file_path)
    print(f"Ses sentezi başarılı! '{input_text[:15]}...' metni için sentezlenen ses şuraya kaydedildi: {generated_speech_file_path}")
    
    return generated_speech_file_path    