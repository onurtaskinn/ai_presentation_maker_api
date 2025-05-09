#%%
from data.datamodels import PresentationOutline, TopicCount, ValidationWithOutline, OutlineValidationResult
from utils.prompts import outline_tester_system_message, outline_tester_user_message
import os, instructor
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()


def call_outline_tester_agent(topic_count: TopicCount, previous_outline: PresentationOutline) -> ValidationWithOutline:
    """Function to call the initial outline generator agent"""

    previous_outline_text = '\n'.join(
        f"{i+1}. {slide.slide_title}\n   Focus: {slide.slide_focus}"
        for i, slide in enumerate(previous_outline.slide_outlines)
    )


    anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    client = instructor.from_anthropic(client=anthropic_client, mode=instructor.Mode.ANTHROPIC_JSON)

    AI_Response, completion = client.chat.completions.create_with_completion(
        model="claude-3-7-sonnet-20250219",
        messages=[
            {
                "role": "system",
                "content": outline_tester_system_message
            },
            {
                "role": "user",
                "content": outline_tester_user_message.format(presentation_topic=topic_count.presentation_topic,
                                                                presentation_title=previous_outline.presentation_title,
                                                                previous_outline_text=previous_outline_text)
            }
        ],
        response_model=OutlineValidationResult,
        top_p=1,
        temperature=0.7,
        max_tokens=8192        
    )

    input_tokens = completion.usage.input_tokens
    output_tokens = completion.usage.output_tokens
    
    return ValidationWithOutline(validation_feedback=AI_Response, tested_outline=previous_outline), input_tokens, output_tokens
