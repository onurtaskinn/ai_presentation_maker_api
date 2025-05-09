#%%
from data.datamodels import RegeneratedPrompt, ImageValidationWithSlideContent, SlideContent
from utils.prompts import image_fixer_system_message, image_fixer_user_message

from anthropic import Anthropic
import os
import instructor
from dotenv import load_dotenv


load_dotenv()

anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
client = instructor.from_anthropic(client=anthropic_client, mode=instructor.Mode.ANTHROPIC_JSON)

#%%

def call_image_fixer_agent(image_validation_result : ImageValidationWithSlideContent) -> SlideContent:
    
    AI_Response, completion = client.chat.completions.create_with_completion(
        model="claude-3-7-sonnet-20250219",
        messages=[
            {
                "role": "system",
                "content": image_fixer_system_message
            },
            {
                "role": "user",
                "content": image_fixer_user_message.format(
                                                            slide_image_prompt = image_validation_result.tested_slide_content.slide_image_prompt,
                                                            slide_onscreen_text = image_validation_result.tested_slide_content.slide_onscreen_text,
                                                            slide_voiceover_text = image_validation_result.tested_slide_content.slide_voiceover_text,

                                                            feedback = image_validation_result.validation_feedback.feedback,
                                                            suggestions = image_validation_result.validation_feedback.suggestions,
                                                            score = image_validation_result.validation_feedback.score
                                                            )
            }
        ],
        response_model=RegeneratedPrompt,
        temperature=0.7,
        max_tokens=8192,
        top_p=1,
    )


    new_slide_content = SlideContent(
        slide_onscreen_text = image_validation_result.tested_slide_content.slide_onscreen_text,
        slide_voiceover_text = image_validation_result.tested_slide_content.slide_voiceover_text,
        slide_image_prompt = AI_Response.prompt
    )

    input_tokens = completion.usage.input_tokens
    output_tokens = completion.usage.output_tokens    
    
    return new_slide_content, input_tokens, output_tokens

#%%
