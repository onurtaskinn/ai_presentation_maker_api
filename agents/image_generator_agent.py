import fal_client
from dotenv import load_dotenv
import requests
import os

load_dotenv()


def call_image_generator_agent(prompt, selected_model):

    handler = fal_client.submit(
        selected_model,
        arguments={
            "prompt": prompt,
            "image_size": "landscape_16_9",
        },
    )

    result = handler.get()
    image_url = result['images'][0]['url']
    return image_url


def download_image_to_local(image_url, presentation_id, slide_number):
    """Download image from URL to local folder"""
    # Create directory if it doesn't exist
    images_dir = f"images/{presentation_id}"
    os.makedirs(images_dir, exist_ok=True)
    
    # Download the image
    response = requests.get(image_url)
    if response.status_code == 200:
        # Get file extension from URL or default to .jpg
        file_extension = ".jpg"  # You might want to detect this from the URL or response headers
        local_path = f"{images_dir}/slide_{slide_number}{file_extension}"
        
        with open(local_path, 'wb') as f:
            f.write(response.content)
        
        return local_path
    else:
        raise Exception(f"Failed to download image: {response.status_code}")