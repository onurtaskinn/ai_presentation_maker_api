#%%
from data.datamodels import ImageValidationResult, SlideContent, ImageValidationWithSlideContent
from utils.prompts import image_tester_system_message, image_tester_user_message

from anthropic import Anthropic
import os
import instructor
from dotenv import load_dotenv


load_dotenv()

anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
client = instructor.from_anthropic(client=anthropic_client, mode=instructor.Mode.ANTHROPIC_JSON)

#%%

def call_image_tester_agent(image_url: str, slide_content : SlideContent) -> ImageValidationWithSlideContent:

    AI_Response, completion = client.chat.completions.create_with_completion(
        model="claude-3-7-sonnet-20250219",        
        messages=[
            {
                "role": "system",
                "content": image_tester_system_message,
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": image_tester_user_message.format(slide_onscreen_text = slide_content.slide_onscreen_text,
                                                                 slide_voiceover_text = slide_content.slide_voiceover_text,
                                                                 slide_image_prompt = slide_content.slide_image_prompt),
                    },
                    {
                        "type": "image",
                        "source": image_url,
                    },
                ],
            }
        ],
        autodetect_images=True,
        response_model=ImageValidationResult,  
        max_tokens=8192,
    )

    input_tokens = completion.usage.input_tokens
    output_tokens = completion.usage.output_tokens

    return ImageValidationWithSlideContent( validation_feedback = AI_Response, tested_slide_content = slide_content) , input_tokens, output_tokens
#%%
