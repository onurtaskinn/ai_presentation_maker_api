# api/presentation.py
from fastapi import Depends, BackgroundTasks, Request
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.responses import FileResponse
from fastapi.responses import Response

import os
import uuid
from datetime import datetime
import time
from typing import Dict, Any
from datetime import timedelta, timezone
from elevenlabs import VoiceSettings
import zipfile
import io
import json


from api.app import app, presentations, save_presentation
from api.app import OUTLINE_THRESHOLD_SCORE, CONTENT_THRESHOLD_SCORE, IMAGE_THRESHOLD_SCORE
from api.app import IMAGE_QUALITY_MODELS
from data.datamodels import TopicCount, FullPresentationRequest, PresentationStatusResponse
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
from agents.image_generator_agent import call_image_generator_agent
from agents.image_tester_agent import call_image_tester_agent
from agents.image_fixer_agent import call_image_fixer_agent
from agents.voice_helper import generate_speech_with_elevenlabs, delete_directory



async def generate_full_presentation_task(
        presentation_id: str, 
        topic: str, 
        slide_count: int, 
        image_quality: str, 
        generate_voiceover:bool, 
        is_agentic: bool, 
        client_id: str, 
        voice_id: int = 1,
        organization_code: str = None, 
        db: Session = None):
    

    start_time = time.time()
    total_tokens = 0
    
    try:
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

        if is_agentic:
            try:
                presentations[presentation_id]["status"] = "generating_outline"
                presentations[presentation_id]["progress"] = {"current_step": "outline", "completion": 0}
                
                # Step 1: Generate outline
                topic_count = TopicCount(presentation_topic=topic, slide_count=slide_count)
                outline, input_tokens, output_tokens = call_outline_initial_generator_agent(topic_count)
                total_tokens = input_tokens + output_tokens
                
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
                
                # Model for image generation
                model = IMAGE_QUALITY_MODELS.get(image_quality.lower(), IMAGE_QUALITY_MODELS["medium"])
                
                # List to store slide data for database
                slides_to_save = []
                
                # Step 4: Generate content and images for each slide
                for i, slide in enumerate(outline.slide_outlines):
                    slide_progress = 30 + (i / slide_count) * 70
                    presentations[presentation_id]["progress"] = {
                        "current_step": f"slide_{i+1}",
                        "current_slide": i+1,
                        "total_slides": slide_count,
                        "completion": int(slide_progress)
                    }
                    
                    # Generate content
                    content, input_tokens, output_tokens = call_content_initial_generator_agent(
                        outline.presentation_title, slide
                    )
                    total_tokens += input_tokens + output_tokens
                    
                    # Test content
                    content_test, input_tokens, output_tokens = call_content_tester_agent(
                        outline.presentation_title, slide, content
                    )
                    total_tokens += input_tokens + output_tokens
                    
                    # Fix content if needed
                    max_attempts = 1
                    while content_test.score < CONTENT_THRESHOLD_SCORE and max_attempts > 0:
                        fixed_content, input_tokens, output_tokens = call_content_fixer_agent(
                            outline.presentation_title, slide, content, content_test
                        )
                        total_tokens += input_tokens + output_tokens   
                        content = fixed_content

                        content_test, input_tokens, output_tokens = call_content_tester_agent(
                            outline.presentation_title, slide, fixed_content
                        )
                        total_tokens += input_tokens + output_tokens    
                        max_attempts -= 1

                    
                    # Generate image
                    image_url = call_image_generator_agent(content.slide_image_prompt, model)
                    
                    # Test image
                    image_test_result, input_tokens, output_tokens = call_image_tester_agent(image_url, content)
                    total_tokens += input_tokens + output_tokens
                    
                    # Fix image prompt if needed
                    max_attempts = 1
                    while image_test_result.validation_feedback.score < IMAGE_THRESHOLD_SCORE and max_attempts > 0:
                        improved_content, input_tokens, output_tokens = call_image_fixer_agent(image_test_result)
                        total_tokens += input_tokens + output_tokens
                        
                        # Regenerate image with improved prompt
                        image_url = call_image_generator_agent(improved_content.slide_image_prompt, model)

                        image_test_result, input_tokens, output_tokens = call_image_tester_agent(image_url, content)
                        total_tokens += input_tokens + output_tokens

                        content = improved_content
                        max_attempts -= 1

                    if generate_voiceover:
                        # Generate voiceover

                        host_voice_settings = VoiceSettings(
                            stability=0.5,
                            similarity_boost=0.75, 
                            speed=1.05,
                        )

                        # example voice id

                        voice_db = crud.get_voice_setting(db, voice_id)
                        voice = schemas.VOICE_SETTINGS.model_validate(voice_db)
                        elevenlabs_voice_id = voice.elevenlabs_voice_id


                        voiceover_filepath = generate_speech_with_elevenlabs(
                            elevenlabs_voice_id=elevenlabs_voice_id,
                            host_voice_settings=host_voice_settings,
                            slide_voiceover_text=content.slide_voiceover_text,
                            output_file_name=f"slide_{i+1}",
                            output_directory=f"audio_files/{presentation_id}"
                        )
                        print(f"Generated voiceover for slide {i+1}: {voiceover_filepath}") 
                        

                    
                    # Create a slide dict for in-memory storage
                    slide_data = {
                        "number": i+1,
                        "title": slide.slide_title,
                        "focus": slide.slide_focus,
                        "onscreen_text": content.slide_onscreen_text,
                        "voiceover_text": content.slide_voiceover_text,
                        "image_prompt": content.slide_image_prompt,
                        "image_url": image_url
                    }
                    
                    # Add to presentation data
                    presentation_data["slides"].append(slide_data)
                    
                    # Create slide data for database
                    slide_to_save = schemas.PRESENTATION_SLIDESCreate(
                        presentation_id=presentation_id,
                        slide_number=i+1,
                        slide_title=slide.slide_title,
                        slide_focus=slide.slide_focus,
                        onscreen_text=content.slide_onscreen_text,
                        voiceover_text=content.slide_voiceover_text,
                        image_prompt=content.slide_image_prompt,
                        image_url=image_url
                    )
                    slides_to_save.append(slide_to_save)
                
                # Update presentation metadata
                presentation_data["tokens_used"] = total_tokens
                
                # Save slides to database
                if db and slides_to_save:
                    crud.create_presentation_slides_batch(db, slides_to_save)
                
                # Save presentation to file
                filepath = save_presentation(presentation_data, presentation_id)
                presentations[presentation_id]["filepath"] = filepath
                presentations[presentation_id]["data"] = presentation_data
                presentations[presentation_id]["status"] = "completed"
                presentations[presentation_id]["progress"] = {"completion": 100}
            
            except Exception as e:
                presentations[presentation_id]["status"] = "error"
                presentations[presentation_id]["error"] = str(e)

        else:
            try:
                presentations[presentation_id]["status"] = "generating_outline"
                presentations[presentation_id]["progress"] = {"current_step": "outline", "completion": 0}
                
                # Step 1: Generate outline
                topic_count = TopicCount(presentation_topic=topic, slide_count=slide_count)
                outline, input_tokens, output_tokens = call_outline_initial_generator_agent(topic_count)
                total_tokens = input_tokens + output_tokens
            
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
                
                # Model for image generation
                model = IMAGE_QUALITY_MODELS.get(image_quality.lower(), IMAGE_QUALITY_MODELS["medium"])
                
                # List to store slide data for database
                slides_to_save = []
                
                # Generate content and images for each slide
                for i, slide in enumerate(outline.slide_outlines):
                    slide_progress = 30 + (i / slide_count) * 70
                    presentations[presentation_id]["progress"] = {
                        "current_step": f"slide_{i+1}",
                        "current_slide": i+1,
                        "total_slides": slide_count,
                        "completion": int(slide_progress)
                    }
                    
                    # Generate content
                    content, input_tokens, output_tokens = call_content_initial_generator_agent(
                        outline.presentation_title, slide
                    )
                    total_tokens += input_tokens + output_tokens
                                  
                    # Generate image
                    image_url = call_image_generator_agent(content.slide_image_prompt, model)

                    if generate_voiceover:
                        # Generate voiceover

                        # example voice settings for the host
                        host_voice_settings = VoiceSettings(
                            stability=0.5,
                            similarity_boost=0.75, 
                            speed=1.05,
                        )

                        voice_db = crud.get_voice_setting(db, voice_id)
                        voice = schemas.VOICE_SETTINGS.model_validate(voice_db)
                        elevenlabs_voice_id = voice.elevenlabs_voice_id


                        voiceover_filepath = generate_speech_with_elevenlabs(
                            elevenlabs_voice_id=elevenlabs_voice_id,
                            host_voice_settings=host_voice_settings,
                            slide_voiceover_text=content.slide_voiceover_text,
                            output_file_name=f"slide_{i+1}",
                            output_directory=f"audio_files/{presentation_id}"
                        )
                        print(f"Generated voiceover for slide {i+1}: {voiceover_filepath}")                     
                                    
                    # Create a slide dict for in-memory storage
                    slide_data = {
                        "number": i+1,
                        "title": slide.slide_title,
                        "focus": slide.slide_focus,
                        "onscreen_text": content.slide_onscreen_text,
                        "voiceover_text": content.slide_voiceover_text,
                        "image_prompt": content.slide_image_prompt,
                        "image_url": image_url
                    }
                    
                    # Add to presentation data
                    presentation_data["slides"].append(slide_data)
                    
                    # Create slide data for database
                    slide_to_save = schemas.PRESENTATION_SLIDESCreate(
                        presentation_id=presentation_id,
                        slide_number=i+1,
                        slide_title=slide.slide_title,
                        slide_focus=slide.slide_focus,
                        onscreen_text=content.slide_onscreen_text,
                        voiceover_text=content.slide_voiceover_text,
                        image_prompt=content.slide_image_prompt,
                        image_url=image_url
                    )
                    slides_to_save.append(slide_to_save)
                
                # Update presentation metadata
                presentation_data["tokens_used"] = total_tokens
                
                # Save slides to database
                if db and slides_to_save:
                    crud.create_presentation_slides_batch(db, slides_to_save)
                
                # Save presentation to file
                filepath = save_presentation(presentation_data, presentation_id)
                presentations[presentation_id]["filepath"] = filepath
                presentations[presentation_id]["data"] = presentation_data
                presentations[presentation_id]["status"] = "completed"
                presentations[presentation_id]["progress"] = {"completion": 100}
            
            except Exception as e:
                presentations[presentation_id]["status"] = "error"
                presentations[presentation_id]["error"] = str(e)
        
        end_time = time.time()
        generation_time = end_time - start_time
        
        # Update presentation history in the database
        if db:
            crud.update_presentation_history(db, presentation_id, total_tokens, generation_time)
            
    except Exception as e:
        if presentation_id in presentations:
            presentations[presentation_id]["status"] = "error"
            presentations[presentation_id]["error"] = str(e)


@app.post("/generate-presentation", response_model=Dict[str, Any])
async def generate_presentation_sync(
    request: Request,
    presentation_req: FullPresentationRequest, 
    return_audio: bool = True, 
    credentials: HTTPAuthorizationCredentials = Depends(auth_middleware.check_auth),
    db: Session = Depends(get_db)
):
    """Generate a complete presentation synchronously (will take time)"""
    client_info = request.state.client_info
    client_id = client_info.client_id if client_info else "anonymous"
    
    presentation_id = str(uuid.uuid4())
    
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
    
    # Call the function directly (convert the function to be non-async first)
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
    
    # Return the full presentation data
    if presentations[presentation_id]["status"] == "error":
        return {
            "presentation_id": presentation_id,
            "status": "error",
            "error": presentations[presentation_id].get("error", "Unknown error")
        }
    

    if return_audio and presentation_req.generate_voiceover:

        json_data = {
            "presentation_id": presentation_id,
            "status": "completed",
            "data": presentations[presentation_id]["data"]
        }        
        
        # Create a zip file in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:

            json_str = json.dumps(json_data, indent=2, ensure_ascii=False)
            json_bytes = json_str.encode('utf-8')

            zip_file.writestr("presentation_data.json", json_bytes)

            # Get the slide count from the presentation
            slide_count = len(presentations[presentation_id]["data"]["slides"])
            
            # Add each slide's audio file to the zip
            for slide_num in range(1, slide_count + 1):
                # audio_filepath = os.path.join("audio_files", f"{presentation_id}_slide_{slide_num}.mp3")
                audio_filepath = os.path.join("audio_files", presentation_id, f"slide_{slide_num}.mp3")   
                if os.path.exists(audio_filepath):
                    # Add file to zip with a friendly name
                    print(f"Adding {audio_filepath} to zip")
                    zip_file.write(audio_filepath, f"slide_{slide_num}_voiceover.mp3")
        
        # Seek to the beginning of the buffer
        zip_buffer.seek(0)
        # Clean up the audio files directory
        delete_directory(f"audio_files/{presentation_id}")
        
        # Return the zip file
        return Response(
            content=zip_buffer.getvalue(),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={presentation_id}_voiceovers.zip"
            }
        )    
    
    return {
        "presentation_id": presentation_id,
        "status": "completed",
        "data": presentations[presentation_id]["data"]
    }
