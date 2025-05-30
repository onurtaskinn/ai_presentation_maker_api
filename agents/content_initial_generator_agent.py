#%%
from data.datamodels import SlideOutline, SlideContent
from utils.prompts import content_initial_generator_system_message, content_initial_generator_user_message

import os
from dotenv import load_dotenv
import instructor
from anthropic import Anthropic


load_dotenv()


def call_content_initial_generator_agent( presentation_title : str, slide_outline : SlideOutline ) -> SlideContent:
    """Function to call the initial outline generator agent"""

    anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    client = instructor.from_anthropic(client=anthropic_client, mode=instructor.Mode.ANTHROPIC_JSON)
    
    AI_Response, completion = client.chat.completions.create_with_completion(
        model="claude-3-7-sonnet-20250219",
        messages=[
            {
                "role": "system",
                "content": content_initial_generator_system_message
            },
            {
                "role": "user",
                "content": content_initial_generator_user_message.format(presentation_title = presentation_title,
                                                                          slide_title = slide_outline.slide_title, 
                                                                          slide_focus = slide_outline.slide_focus)
            }
        ],
        response_model=SlideContent,
        temperature=0.7,
        max_tokens=8192,
        top_p=1,
    )
    
    input_tokens = completion.usage.input_tokens
    output_tokens = completion.usage.output_tokens
    
    return AI_Response, input_tokens, output_tokens
