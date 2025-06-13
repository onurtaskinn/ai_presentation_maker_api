# api/presentation.py
from fastapi import Depends, Request, UploadFile, File, Form
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.responses import Response

from utils.file_operations import process_uploaded_file
import uuid
from datetime import datetime
import time
from typing import Dict, Any, Tuple
from datetime import timedelta, timezone
from elevenlabs import VoiceSettings
import json


from api.app import app, presentations
from api.app import OUTLINE_THRESHOLD_SCORE, CONTENT_THRESHOLD_SCORE, IMAGE_THRESHOLD_SCORE
from api.app import IMAGE_QUALITY_MODELS
from data.datamodels import TopicCount, FullPresentationRequest, PresentationOutline, SlideContent, SlideOutline
from app.auth_middleware import auth_middleware, get_db
from sqlalchemy.orm import Session
from data.db import crud, schemas

# Import agents
from agents.outline_initial_generator_agent import call_outline_initial_generator_agent
from agents.outline_tester_agent import call_outline_tester_agent
from agents.outline_fixer_agent import call_outline_fixer_agent
from agents.content_initial_generator_agent import call_content_initial_generator_agent
from agents.content_tester_agent import call_content_tester_agent
from agents.content_fixer_agent import call_content_fixer_agent
from agents.image_generator_agent import call_image_generator_agent, download_image_to_local
from agents.image_tester_agent import call_image_tester_agent
from agents.image_fixer_agent import call_image_fixer_agent
from agents.voice_helper import generate_speech_with_elevenlabs, delete_directory
from powepoint_deneme.pptx_generator import create_presentation_from_data


def initialize_presentation_generation(presentation_id: str, topic: str, slide_count: int, 
                                     client_id: str, db: Session = None) -> int:
    """Initialize presentation generation and record in database"""
    total_tokens = 0
    
    # Record the presentation in the database
    if db:
        presentation_history = schemas.PRESENTATION_HISTORYCreate(
            presentation_id=presentation_id,
            topic=topic,
            client_id=client_id,
            slide_count=slide_count,
            total_tokens=0,
            generation_time=0,
            created_on=datetime.now(timezone(timedelta(hours=3)))
        )
        crud.create_presentation_history(db, presentation_history)
    
    return total_tokens


def generate_and_validate_outline(topic: str, slide_count: int, is_agentic: bool, 
                                presentation_id: str) -> Tuple[PresentationOutline, int]:
    """Generate presentation outline with optional validation and fixing"""
    total_tokens = 0
    
    # Update progress
    presentations[presentation_id]["status"] = "generating_outline"
    presentations[presentation_id]["progress"] = {"current_step": "outline", "completion": 0}
    
    # Step 1: Generate outline
    topic_count = TopicCount(presentation_topic=topic, slide_count=slide_count)
    outline, input_tokens, output_tokens = call_outline_initial_generator_agent(topic_count)
    total_tokens += input_tokens + output_tokens
    
    if is_agentic:
        # Step 2: Test outline
        presentations[presentation_id]["progress"] = {"current_step": "testing_outline", "completion": 10}
        test_result, input_tokens, output_tokens = call_outline_tester_agent(topic_count, outline)
        total_tokens += input_tokens + output_tokens
        
        # Step 3: Fix outline if needed
        max_attempts = 1
        while test_result.validation_feedback.score < OUTLINE_THRESHOLD_SCORE and max_attempts > 0:
            presentations[presentation_id]["progress"] = {"current_step": "fixing_outline", "completion": 20}
            fixed_outline, input_tokens, output_tokens = call_outline_fixer_agent(test_result)

            test_result, input_tokens, output_tokens = call_outline_tester_agent(topic_count, fixed_outline)
            total_tokens += input_tokens + output_tokens            

            outline = fixed_outline
            total_tokens += input_tokens + output_tokens
            max_attempts -= 1
    
    return outline, total_tokens


def generate_slide_content(presentation_title: str, slide: SlideOutline, is_agentic: bool) -> Tuple[SlideContent, int]:
    """Generate slide content with optional validation and fixing"""
    total_tokens = 0
    
    # Generate content
    content, input_tokens, output_tokens = call_content_initial_generator_agent(
        presentation_title, slide
    )
    total_tokens += input_tokens + output_tokens
    
    if is_agentic:
        # Test content
        content_test, input_tokens, output_tokens = call_content_tester_agent(
            presentation_title, slide, content
        )
        total_tokens += input_tokens + output_tokens
        
        # Fix content if needed
        max_attempts = 1
        while content_test.score < CONTENT_THRESHOLD_SCORE and max_attempts > 0:
            fixed_content, input_tokens, output_tokens = call_content_fixer_agent(
                presentation_title, slide, content, content_test
            )
            total_tokens += input_tokens + output_tokens   
            content = fixed_content

            content_test, input_tokens, output_tokens = call_content_tester_agent(
                presentation_title, slide, fixed_content
            )
            total_tokens += input_tokens + output_tokens    
            max_attempts -= 1
    
    return content, total_tokens


def generate_and_validate_slide_image(content: SlideContent, image_model: str, 
                                    presentation_id: str, slide_number: int, 
                                    is_agentic: bool) -> Tuple[str, str, int]:
    """Generate slide image with optional validation and fixing"""
    total_tokens = 0
    
    # Generate image
    image_url = call_image_generator_agent(content.slide_image_prompt, image_model)
    
    if is_agentic:
        # Test image
        image_test_result, input_tokens, output_tokens = call_image_tester_agent(image_url, content)
        total_tokens += input_tokens + output_tokens
        
        # Fix image prompt if needed
        max_attempts = 1
        while image_test_result.validation_feedback.score < IMAGE_THRESHOLD_SCORE and max_attempts > 0:
            improved_content, input_tokens, output_tokens = call_image_fixer_agent(image_test_result)
            total_tokens += input_tokens + output_tokens
            
            # Regenerate image with improved prompt
            image_url = call_image_generator_agent(improved_content.slide_image_prompt, image_model)

            image_test_result, input_tokens, output_tokens = call_image_tester_agent(image_url, content)
            total_tokens += input_tokens + output_tokens

            content = improved_content
            max_attempts -= 1

    # Download image locally
    local_image_path = download_image_to_local(image_url, presentation_id, slide_number)
    
    return image_url, local_image_path, total_tokens


def generate_slide_voiceover(content: SlideContent, presentation_id: str, 
                           slide_number: int, voice_id: int, db: Session) -> str:
    """Generate voiceover for a slide"""
    # Voice settings
    host_voice_settings = VoiceSettings(
        stability=0.5,
        similarity_boost=0.75, 
        speed=1.05,
    )

    # Get voice configuration
    voice_db = crud.get_voice_setting(db, voice_id)
    voice = schemas.VOICE_SETTINGS.model_validate(voice_db)
    elevenlabs_voice_id = voice.elevenlabs_voice_id

    # Generate voiceover
    voiceover_filepath = generate_speech_with_elevenlabs(
        elevenlabs_voice_id=elevenlabs_voice_id,
        host_voice_settings=host_voice_settings,
        slide_voiceover_text=content.slide_voiceover_text,
        output_file_name=f"slide_{slide_number}",
        output_directory=f"audio_files/{presentation_id}"
    )
    
    print(f"Generated voiceover for slide {slide_number}: {voiceover_filepath}")
    return voiceover_filepath


def process_single_slide(slide: SlideOutline, slide_index: int, slide_count: int, 
                        presentation_title: str, presentation_id: str, 
                        image_model: str, is_agentic: bool, 
                        generate_voiceover: bool, voice_id: int, db: Session) -> Tuple[Dict, schemas.PRESENTATION_SLIDESCreate, int]:
    """Process a single slide: content, image, voiceover"""
    total_tokens = 0
    slide_number = slide_index + 1
    
    # Update progress
    slide_progress = 30 + (slide_index / slide_count) * 70
    presentations[presentation_id]["progress"] = {
        "current_step": f"slide_{slide_number}",
        "current_slide": slide_number,
        "total_slides": slide_count,
        "completion": int(slide_progress)
    }
    
    # Generate content
    content, content_tokens = generate_slide_content(presentation_title, slide, is_agentic)
    total_tokens += content_tokens
    
    # Generate image
    image_url, local_image_path, image_tokens = generate_and_validate_slide_image(
        content, image_model, presentation_id, slide_number, is_agentic
    )
    total_tokens += image_tokens
    
    # Generate voiceover if requested
    if generate_voiceover:
        generate_slide_voiceover(content, presentation_id, slide_number, voice_id, db)
    
    # Prepare onscreen text for database
    merged_onscreen_text = "\n".join(content.slide_onscreen_text.text_list)

    # Create slide data for in-memory storage
    slide_data = {
        "number": slide_number,
        "title": slide.slide_title,
        "focus": slide.slide_focus,
        "content": content,
        "image_url": image_url
    }
    
    # Create slide data for database
    slide_to_save = schemas.PRESENTATION_SLIDESCreate(
        presentation_id=presentation_id,
        slide_number=slide_number,
        slide_title=slide.slide_title,
        slide_focus=slide.slide_focus,
        onscreen_text=merged_onscreen_text,
        voiceover_text=content.slide_voiceover_text,
        image_prompt=content.slide_image_prompt,
        image_url=image_url
    )
    
    return slide_data, slide_to_save, total_tokens


def finalize_presentation(presentation_data: Dict, slides_to_save: list, 
                        presentation_id: str, total_tokens: int, 
                        db: Session, start_time: float) -> None:
    """Finalize presentation: save to database, create PowerPoint, cleanup"""
    
    # Update presentation metadata
    presentation_data["tokens_used"] = total_tokens
    
    # Save slides to database
    if db and slides_to_save:
        crud.create_presentation_slides_batch(db, slides_to_save)
    
    # Save presentation to file
    presentations[presentation_id]["data"] = presentation_data
    presentations[presentation_id]["status"] = "completed"
    presentations[presentation_id]["progress"] = {"completion": 100}
    
    # Calculate generation time and update database
    end_time = time.time()
    generation_time = end_time - start_time

    if db:
        crud.update_presentation_history(db, presentation_id, total_tokens, generation_time)


def create_presentation_files(presentation_data: Dict, presentation_id: str, 
                            slide_count: int, generate_voiceover: bool) -> str:
    """Create PowerPoint file and handle cleanup"""
    
    # Create PowerPoint file (will use the already downloaded local images)
    print("Creating PowerPoint presentation...")
    pptx_file_path = create_presentation_from_data(presentation_data)
    
    if pptx_file_path:
        print(f"✓ PowerPoint file created: {pptx_file_path}")
    else:
        print("⚠ Warning: PowerPoint creation failed, continuing without PPTX file")

    # Clean up temporary files (do this AFTER creating PowerPoint)
    delete_directory(f"audio_files/{presentation_id}")
    delete_directory(f"images/{presentation_id}")
    
    return pptx_file_path


async def generate_full_presentation_task(
        presentation_id: str, 
        topic: str, 
        slide_count: int, 
        image_quality: str, 
        generate_voiceover: bool, 
        is_agentic: bool, 
        client_id: str, 
        voice_id: int = 1,
        organization_code: str = None, 
        db: Session = None):
    
    start_time = time.time()
    
    try:
        # Initialize presentation generation
        total_tokens = initialize_presentation_generation(
            presentation_id, topic, slide_count, client_id, db
        )

        # Generate and validate outline
        outline, outline_tokens = generate_and_validate_outline(
            topic, slide_count, is_agentic, presentation_id
        )
        total_tokens += outline_tokens
        
        # Prepare presentation data structure
        presentation_data = {
            "id": presentation_id,
            "title": outline.presentation_title,
            "topic": topic,
            "slide_count": slide_count,
            "creation_time": datetime.now().isoformat(),
            "tokens_used": total_tokens,
            "organization_code": organization_code,
            "slides": []
        }
        
        # Get image model
        model = IMAGE_QUALITY_MODELS.get(image_quality.lower(), IMAGE_QUALITY_MODELS["medium"])
        
        # List to store slide data for database
        slides_to_save = []
        
        # Process each slide
        for i, slide in enumerate(outline.slide_outlines):
            slide_data, slide_to_save, slide_tokens = process_single_slide(
                slide, i, slide_count, outline.presentation_title, presentation_id,
                model, is_agentic, generate_voiceover, voice_id, db
            )
            
            total_tokens += slide_tokens
            presentation_data["slides"].append(slide_data)
            slides_to_save.append(slide_to_save)
        
        # Finalize presentation
        finalize_presentation(
            presentation_data, slides_to_save, presentation_id, 
            total_tokens, db, start_time
        )
            
    except Exception as e:
        if presentation_id in presentations:
            presentations[presentation_id]["status"] = "error"
            presentations[presentation_id]["error"] = str(e)


@app.post("/generate-presentation", response_model=Dict[str, Any])
async def generate_presentation_sync(
    request: Request,
    presentation_req: str = Form(...),
    file: UploadFile = File(...),
    credentials: HTTPAuthorizationCredentials = Depends(auth_middleware.check_auth),
    db: Session = Depends(get_db)
):
    """Generate a complete presentation synchronously (will take time)"""

    presentation_req = FullPresentationRequest.model_validate_json(presentation_req)
    client_info = request.state.client_info
    client_id = client_info.client_id if client_info else "anonymous"
    
    presentation_id = str(uuid.uuid4())
    print(f"Generating presentation with ID: {presentation_id} for client: {client_id}")    


    extracted_text = await process_uploaded_file(file)

    print(f"Extracted text from uploaded file: {extracted_text[:100]}...")  # Print first 100 characters for debugging

    # Initialize presentation in storage
    presentations[presentation_id] = {
        "status": "processing",
        "creation_time": datetime.now().isoformat(),
        "request": {
            "topic": presentation_req.topic,
            "slide_count": presentation_req.slide_count,
            "image_quality": presentation_req.image_quality,
            "is_agentic": presentation_req.is_agentic,
            "organization_code": presentation_req.organization_code,
            "voice_id": presentation_req.voice_id
        }
    }
    
    # Generate the presentation
    await generate_full_presentation_task(
        presentation_id=presentation_id,
        topic=presentation_req.topic,
        slide_count=presentation_req.slide_count,
        image_quality=presentation_req.image_quality,
        generate_voiceover=presentation_req.generate_voiceover,
        is_agentic=presentation_req.is_agentic,
        client_id=client_id,
        voice_id=presentation_req.voice_id,
        organization_code=presentation_req.organization_code,
        db=db
    )

    # Return error if generation failed
    if presentations[presentation_id]["status"] == "error":
        return {
            "presentation_id": presentation_id,
            "status": "error",
            "error": presentations[presentation_id].get("error", "Unknown error")
        }
    
    # Get presentation data
    data = presentations[presentation_id]["data"]
    presentation_title = data["title"]
    slide_count = data["slide_count"]

    # Create PowerPoint and cleanup
    pptx_file_path = create_presentation_files(
        data, presentation_id, slide_count, presentation_req.generate_voiceover
    )

    return_response = {
        "presentation_id": presentation_id,
        "status": "completed",
        "data": {
            "title": presentation_title,
            "slide_count": slide_count,
            "pptx_file_path": pptx_file_path
        }
    }
    
    return Response(
        content=json.dumps(return_response),
        media_type="application/json"
    )