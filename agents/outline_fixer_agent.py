#%%
from data.datamodels import PresentationOutline, ValidationWithOutline
from utils.prompts import outline_fixer_system_message, outline_fixer_user_message

import os, instructor
from dotenv import load_dotenv
from anthropic import Anthropic


load_dotenv()


def call_outline_fixer_agent(test_result_with_outline : ValidationWithOutline) -> PresentationOutline:
    """Function to call the outline fixer agent"""
    
    previous_outline = test_result_with_outline.tested_outline
    feedback = test_result_with_outline.validation_feedback.feedback
    score = test_result_with_outline.validation_feedback.score

    previous_outline_text = '\n'.join(
        f"{i+1}. {slide.slide_title}\n   Focus: {slide.slide_focus}"
        for i, slide in enumerate(previous_outline.slide_outlines)
    )
    previous_outline_title = previous_outline.presentation_title

    anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    client = instructor.from_anthropic(client=anthropic_client, mode=instructor.Mode.ANTHROPIC_JSON)

    AI_Response, completion = client.chat.completions.create_with_completion(
        model="claude-3-7-sonnet-20250219",
        messages=[
            {
                "role": "system",
                "content": outline_fixer_system_message
            },
            {
                "role": "user",
                "content": outline_fixer_user_message.format( previous_outline_title=previous_outline_title,
                                                              slide_count=len(previous_outline.slide_outlines),
                                                              previous_outline_text=previous_outline_text,
                                                              feedback=feedback,
                                                              score=score)
            }
        ],
        response_model=PresentationOutline,
        temperature=0.7,
        max_tokens=8192,
        top_p=1,
    )

    input_tokens = completion.usage.input_tokens
    output_tokens = completion.usage.output_tokens
    
    return AI_Response, input_tokens, output_tokens