import fal_client
from dotenv import load_dotenv
import requests
import os
from PIL import Image
from io import BytesIO

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
    """Download image from URL to local folder and convert to JPEG format"""
    # Create directory if it doesn't exist
    images_dir = f"images/{presentation_id}"
    os.makedirs(images_dir, exist_ok=True)
    
    try:
        # Download the image
        response = requests.get(image_url, timeout=30)
        if response.status_code == 200:
            # Load image data into PIL
            image_data = BytesIO(response.content)
            
            # Open with PIL to detect and convert format
            with Image.open(image_data) as img:
                # Convert to RGB if necessary (handles RGBA, P mode, etc.)
                if img.mode in ('RGBA', 'LA', 'P'):
                    # Create white background for transparent images
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                    img = rgb_img
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Save as JPEG
                local_path = f"{images_dir}/slide_{slide_number}.jpg"
                img.save(local_path, 'JPEG', quality=95, optimize=True)
                
                print(f"✓ Image converted and saved: {local_path}")
                return local_path
        else:
            raise Exception(f"Failed to download image: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"Error downloading/converting image: {e}")
        raise Exception(f"Failed to download and convert image: {str(e)}")