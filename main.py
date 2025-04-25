import os
import time
from dotenv import load_dotenv
from utils.datamodels import TopicCount, SlideContent, ValidationWithOutline, ImageValidationWithSlideContent

# Import generator agents
from agents.outline_initial_generator_agent import call_outline_initial_generator_agent
from agents.content_initial_generator_agent import call_content_initial_generator_agent
from agents.image_generator_agent import call_image_generator_agent

# Import tester agents
from agents.outline_tester_agent import call_outline_tester_agent
from agents.content_tester_agent import call_content_tester_agent
from agents.image_tester_agent import call_image_tester_agent

# Import fixer agents
from agents.outline_fixer_agent import call_outline_fixer_agent
from agents.content_fixer_agent import call_content_fixer_agent
from agents.image_fixer_agent import call_image_fixer_agent

# Quality thresholds
OUTLINE_THRESHOLD_SCORE = 80 # out of 100
CONTENT_THRESHOLD_SCORE = 14 # out of 17
IMAGE_THRESHOLD_SCORE = 10 # out of 13

# Load environment variables
load_dotenv()

def generate_presentation(topic, slide_count, image_model="fal-ai/imagen3"):
    """Generate a complete presentation with the specified topic and slide count"""
    print(f"Generating presentation on: {topic} with {slide_count} slides")
    total_tokens = 0
    
    # Step 1: Generate and validate outline
    print("Creating outline...")
    topic_count = TopicCount(presentation_topic=topic, slide_count=slide_count)
    outline, input_tokens, output_tokens = call_outline_initial_generator_agent(topic_count)
    total_tokens += input_tokens + output_tokens
    
    # Test outline quality
    print("Testing outline quality...")
    test_result, input_tokens, output_tokens = call_outline_tester_agent(topic_count, outline)
    total_tokens += input_tokens + output_tokens
    
    # Fix outline if needed
    if test_result.validation_feedback.score < OUTLINE_THRESHOLD_SCORE:
        print(f"Outline needs improvement (Score: {test_result.validation_feedback.score})")
        print(f"Feedback: {test_result.validation_feedback.feedback}")
        print("Fixing outline...")
        fixed_outline, input_tokens, output_tokens = call_outline_fixer_agent(test_result)
        outline = fixed_outline
        total_tokens += input_tokens + output_tokens
    
    print(f"Final outline created: {outline.presentation_title}")
    
    # Step 2: Generate content and images for each slide
    presentation = {
        "title": outline.presentation_title,
        "slides": []
    }
    
    for i, slide in enumerate(outline.slide_outlines):
        print(f"\nProcessing slide {i+1}/{slide_count}: {slide.slide_title}")
        
        # Generate initial content
        print("Generating content...")
        content, input_tokens, output_tokens = call_content_initial_generator_agent(
            outline.presentation_title, slide
        )
        total_tokens += input_tokens + output_tokens
        
        # Test content quality
        print("Testing content quality...")
        content_test, input_tokens, output_tokens = call_content_tester_agent(
            outline.presentation_title, slide, content
        )
        total_tokens += input_tokens + output_tokens
        
        # Fix content if needed
        if content_test.score < CONTENT_THRESHOLD_SCORE:
            print(f"Content needs improvement (Score: {content_test.score})")
            print("Fixing content...")
            fixed_content, input_tokens, output_tokens = call_content_fixer_agent(
                outline.presentation_title, slide, content, content_test
            )
            content = fixed_content
            total_tokens += input_tokens + output_tokens
        
        # Generate image
        print("Generating image...")
        image_url = call_image_generator_agent(content.slide_image_prompt, image_model)
        
        # Test image quality
        print("Testing image quality...")
        image_test_result, input_tokens, output_tokens = call_image_tester_agent(image_url, content)
        total_tokens += input_tokens + output_tokens
        
        # Fix image prompt if needed
        if image_test_result.validation_feedback.score < IMAGE_THRESHOLD_SCORE:
            print(f"Image needs improvement (Score: {image_test_result.validation_feedback.score})")
            print("Fixing image prompt and regenerating...")
            improved_content, input_tokens, output_tokens = call_image_fixer_agent(image_test_result)
            total_tokens += input_tokens + output_tokens
            
            # Regenerate image with improved prompt
            image_url = call_image_generator_agent(improved_content.slide_image_prompt, image_model)
            content = improved_content  # Update content with improved image prompt
        
        # Store slide data
        presentation["slides"].append({
            "number": i+1,
            "title": slide.slide_title,
            "focus": slide.slide_focus,
            "onscreen_text": content.slide_onscreen_text,
            "voiceover_text": content.slide_voiceover_text,
            "image_prompt": content.slide_image_prompt,
            "image_url": image_url
        })
        
        print(f"Slide {i+1} completed")
    
    print(f"\nPresentation generation complete! Total tokens used: {total_tokens}")
    return presentation


def save_presentation(presentation, filename=None):
    """Save the presentation to a JSON file with optional custom filename"""
    import json
    from datetime import datetime
    
    # Generate default filename with timestamp if none provided
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"presentation_detailed_{timestamp}.json"
    
    os.makedirs("_outputs", exist_ok=True)
    filepath = os.path.join("_outputs", filename)
    
    with open(filepath, "w") as f:
        json.dump(presentation, f, indent=2)
    
    print(f"Presentation saved to {filepath}")
    return filepath

if __name__ == "__main__":
    # Simple command-line interface
    topic = input("Enter presentation topic: ") or "Effective Communication in Business"
    slide_count = int(input("Enter number of slides (2-15): ") or "5")
    
    # Image quality options
    quality_options = {
        "1": ("Low", "fal-ai/recraft-20b"),
        "2": ("Medium", "fal-ai/imagen3"),
        "3": ("High", "fal-ai/flux-pro/v1.1")
    }
    
    print("\nImage Quality Options:")
    for key, (name, _) in quality_options.items():
        print(f"{key}: {name}")
    
    quality_choice = input("Select image quality (1-3): ") or "2"
    quality_name, image_model = quality_options.get(quality_choice, quality_options["2"])
    
    print(f"\nSelected: {quality_name} quality")
    
    # Ensure valid slide count
    slide_count = max(2, min(slide_count, 15))
    
    # Generate presentation
    presentation = generate_presentation(topic, slide_count, image_model)
    
    # Save results
    save_presentation(presentation)
    
    # Display summary
    print("\nPresentation Summary:")
    print(f"Title: {presentation['title']}")
    print(f"Slides: {len(presentation['slides'])}")
    for slide in presentation['slides']:
        print(f"  - Slide {slide['number']}: {slide['title']}")