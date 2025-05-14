from elevenlabs import VoiceSettings
# from data.datamodels import Persona
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
from pydub import AudioSegment
import os
from dotenv import load_dotenv

load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

AUDIO_OUTPUT_DIRECTORY = "./audio"
DEFAULT_ELEVENLABS_MODEL = "eleven_turbo_v2_5"  #eleven_turbo_v2_5, eleven_multilingual_v2





def create_clean_audio_directory(directory_name: str):
    """
    Creates a clean directory under ./audio with the given name.
    If directory already exists, deletes it and its contents first.
    
    Args:
        directory_name (str): Name of the directory to create
    """
    full_path = os.path.join(AUDIO_OUTPUT_DIRECTORY, directory_name)
    
    # Delete directory if it exists
    if os.path.exists(full_path):
        for file in os.listdir(full_path):
            file_path = os.path.join(full_path, file)
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                os.rmdir(file_path)
        os.rmdir(full_path)
        
    # Create new directory
    os.makedirs(full_path)

    return full_path


def ensure_directory_exists(directory_path):
    """Create the directory if it doesn't exist."""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
        print(f"Created directory: {directory_path}")
    else:
        print(f"Directory already exists: {directory_path}")


def delete_directory(directory_path):
    """Delete the directory and its contents."""
    if os.path.exists(directory_path):
        for file in os.listdir(directory_path):
            file_path = os.path.join(directory_path, file)
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                delete_directory(file_path)
        os.rmdir(directory_path)
        print(f"Deleted directory: {directory_path}")
    else:
        print(f"Directory does not exist: {directory_path}")


def combine_mp3_files(output_file_name:str, partial_audio_files_directory:str):

    mp3_files = [f for f in os.listdir(partial_audio_files_directory) if f.endswith('.mp3')]

    mp3_files.sort(key=lambda x: int(x.split('.')[0]))
    
    combined_audio = AudioSegment.empty()
    
    for mp3_file in mp3_files:
        file_path = os.path.join(partial_audio_files_directory, mp3_file)
        audio = AudioSegment.from_mp3(file_path)
        combined_audio += audio

    completed_podcast_filepath = f"./{partial_audio_files_directory}/{output_file_name}.mp3"
    combined_audio.export(out_f=completed_podcast_filepath, format="mp3")

    return completed_podcast_filepath


def generate_speech_with_elevenlabs(
                                    elevenlabs_voice_id: str, 
                                    slide_voiceover_text: str,
                                    host_voice_settings: VoiceSettings, 
                                    output_file_name: str, output_directory: str = None) -> bool:
    """
    Generates speech audio using ElevenLabs API based on the provided text and persona.
    
    Args:
        speaker (Persona): The persona object containing voice settings and voice ID.
        dialogue_text (str): The text content to be converted to speech.
        output_file_name (str): Name for the output MP3 file (without extension).
        output_directory (str, optional): The directory where the audio file will be saved. 
                                          Defaults to None, which uses the global AUDIO_OUTPUT_DIRECTORY.
        
    Returns:
        bool: True if speech generation and saving was successful, False otherwise.
        
    Note:
        The function saves the generated audio as an MP3 file in the specified directory.
    """



    try:
        client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

        response = client.text_to_speech.convert(
            voice_id=elevenlabs_voice_id,
            optimize_streaming_latency="0", 
            output_format="mp3_22050_32",
            text=slide_voiceover_text,
            model_id=DEFAULT_ELEVENLABS_MODEL,
            voice_settings=host_voice_settings,
        )

        # Use the provided output_directory or default to AUDIO_OUTPUT_DIRECTORY
        if output_directory is None:
            output_directory = AUDIO_OUTPUT_DIRECTORY
        else:
            ensure_directory_exists(output_directory)

        output_file_path = os.path.join(output_directory, f"{output_file_name}.mp3")

        with open(output_file_path, "wb") as f:
            for chunk in response:
                if chunk:
                    f.write(chunk)
        
        return True

    except Exception as e:
        print(f"Error occured while generating speech: {str(e)}")
        return False