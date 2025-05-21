# api/endpoints.py
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials
from typing import Dict, Any, List, Optional
import json
from datetime import datetime

from api.app import app, presentations
from data.datamodels import (
    TopicCount, SlideOutline, PresentationOutline, 
    SlideContent, OutlineRequest, ContentRequest, ImageRequest, 
    ImageValidationResult, ValidationWithOutline, ValidationWithContent,
    ImageValidationWithSlideContent, ContentValidationResult,
    RegeneratedPrompt, OutlineValidationResult
)
from data.db import crud, schemas

from app.auth_middleware import auth_middleware, get_db
from sqlalchemy.orm import Session

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
from api.app import IMAGE_QUALITY_MODELS

@app.get("/")
def read_root():
    return {"message": "AI Presentation Generator API", "version": "1.0.0"}



@app.post("/generate-outline", response_model=Dict[str, Any])
async def generate_outline(
    request: Request,
    outline_req: OutlineRequest,
    credentials: HTTPAuthorizationCredentials = Depends(auth_middleware.check_auth),
    db: Session = Depends(get_db)
):
    """Generate a presentation outline based on topic and slide count"""
    client_info = request.state.client_info
    
    try:
        topic_count = TopicCount(
            presentation_topic=outline_req.topic,
            slide_count=outline_req.slide_count
        )
        
        outline, input_tokens, output_tokens = call_outline_initial_generator_agent(topic_count)
        
        return {
            "outline": json.loads(outline.model_dump_json()),
            "tokens": {
                "input": input_tokens,
                "output": output_tokens,
                "total": input_tokens + output_tokens
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/test-outline", response_model=Dict[str, Any])
async def test_outline(
    request: Request,
    test_req: Dict[str, Any],
    credentials: HTTPAuthorizationCredentials = Depends(auth_middleware.check_auth),
    db: Session = Depends(get_db)
):
    """Test a presentation outline for quality"""
    client_info = request.state.client_info
    
    try:
        topic_count = TopicCount(
            presentation_topic=test_req.get("topic"),
            slide_count=len(test_req.get("outline", {}).get("slide_outlines", []))
        )
        
        outline = PresentationOutline.model_validate(test_req.get("outline"))
        
        test_result, input_tokens, output_tokens = call_outline_tester_agent(topic_count, outline)
        
        return {
            "test_result": json.loads(test_result.model_dump_json()),
            "tokens": {
                "input": input_tokens,
                "output": output_tokens,
                "total": input_tokens + output_tokens
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/fix-outline", response_model=Dict[str, Any])
async def fix_outline(
    request: Request,
    fix_req: Dict[str, Any],
    credentials: HTTPAuthorizationCredentials = Depends(auth_middleware.check_auth),
    db: Session = Depends(get_db)
):
    """Fix a presentation outline based on test feedback"""
    client_info = request.state.client_info
    
    try:
        # Create ValidationWithOutline from request
        outline = PresentationOutline.model_validate(fix_req.get("outline"))
        
        validation_result = OutlineValidationResult(
            feedback=fix_req.get("feedback", ""),
            score=fix_req.get("score", 0)
        )
        
        validation_with_outline = ValidationWithOutline(
            validation_feedback=validation_result,
            tested_outline=outline
        )
        
        fixed_outline, input_tokens, output_tokens = call_outline_fixer_agent(validation_with_outline)
        
        return {
            "fixed_outline": json.loads(fixed_outline.model_dump_json()),
            "tokens": {
                "input": input_tokens,
                "output": output_tokens,
                "total": input_tokens + output_tokens
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-content", response_model=Dict[str, Any])
async def generate_content(
    request: Request,
    content_req: ContentRequest,
    credentials: HTTPAuthorizationCredentials = Depends(auth_middleware.check_auth),
    db: Session = Depends(get_db)
):
    """Generate content for a slide"""
    client_info = request.state.client_info
    
    try:
        content, input_tokens, output_tokens = call_content_initial_generator_agent(
            content_req.presentation_title,
            content_req.slide
        )
        
        return {
            "content": json.loads(content.model_dump_json()),
            "tokens": {
                "input": input_tokens,
                "output": output_tokens,
                "total": input_tokens + output_tokens
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/test-content", response_model=Dict[str, Any])
async def test_content(
    request: Request,
    test_content_req: Dict[str, Any],
    credentials: HTTPAuthorizationCredentials = Depends(auth_middleware.check_auth),
    db: Session = Depends(get_db)
):
    """Test slide content for quality"""
    client_info = request.state.client_info
    
    try:
        presentation_title = test_content_req.get("presentation_title", "")
        slide = SlideOutline.model_validate(test_content_req.get("slide", {}))
        content = SlideContent.model_validate(test_content_req.get("content", {}))
        
        test_result, input_tokens, output_tokens = call_content_tester_agent(
            presentation_title, 
            slide, 
            content
        )
        
        return {
            "test_result": json.loads(test_result.model_dump_json()),
            "tokens": {
                "input": input_tokens,
                "output": output_tokens,
                "total": input_tokens + output_tokens
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/fix-content", response_model=Dict[str, Any])
async def fix_content(
    request: Request,
    fix_content_req: Dict[str, Any],
    credentials: HTTPAuthorizationCredentials = Depends(auth_middleware.check_auth),
    db: Session = Depends(get_db)
):
    """Fix slide content based on test feedback"""
    client_info = request.state.client_info
    
    try:
        presentation_title = fix_content_req.get("presentation_title", "")
        slide = SlideOutline.model_validate(fix_content_req.get("slide", {}))
        content = SlideContent.model_validate(fix_content_req.get("content", {}))
        
        validation_result = ContentValidationResult(
            feedback=fix_content_req.get("feedback", ""),
            score=fix_content_req.get("score", 0)
        )
        
        fixed_content, input_tokens, output_tokens = call_content_fixer_agent(
            presentation_title,
            slide,
            content,
            validation_result
        )
        
        return {
            "fixed_content": json.loads(fixed_content.model_dump_json()),
            "tokens": {
                "input": input_tokens,
                "output": output_tokens,
                "total": input_tokens + output_tokens
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-image", response_model=Dict[str, Any])
async def generate_image(
    request: Request,
    image_req: ImageRequest,
    credentials: HTTPAuthorizationCredentials = Depends(auth_middleware.check_auth),
    db: Session = Depends(get_db)
):
    """Generate an image based on a prompt"""
    client_info = request.state.client_info
    
    try:
        model = IMAGE_QUALITY_MODELS.get(image_req.quality.lower(), IMAGE_QUALITY_MODELS["medium"])
        
        image_url = call_image_generator_agent(image_req.image_prompt, model)
        
        return {
            "image_url": image_url,
            "model_used": model
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/test-image", response_model=Dict[str, Any])
async def test_image(
    request: Request,
    test_image_req: Dict[str, Any],
    credentials: HTTPAuthorizationCredentials = Depends(auth_middleware.check_auth),
    db: Session = Depends(get_db)
):
    """Test an image for quality and relevance"""
    client_info = request.state.client_info
    
    try:
        image_url = test_image_req.get("image_url", "")
        content = SlideContent.model_validate(test_image_req.get("content", {}))
        
        test_result, input_tokens, output_tokens = call_image_tester_agent(
            image_url,
            content
        )
        
        return {
            "test_result": json.loads(test_result.model_dump_json()),
            "tokens": {
                "input": input_tokens,
                "output": output_tokens,
                "total": input_tokens + output_tokens
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/fix-image-prompt", response_model=Dict[str, Any])
async def fix_image_prompt(
    request: Request,
    fix_image_req: Dict[str, Any],
    credentials: HTTPAuthorizationCredentials = Depends(auth_middleware.check_auth),
    db: Session = Depends(get_db)
):
    """Fix an image prompt based on test feedback"""
    client_info = request.state.client_info
    
    try:
        content = SlideContent.model_validate(fix_image_req.get("content", {}))
        validation_result = ImageValidationResult.model_validate(fix_image_req.get("validation_result", {}))
        
        validation_with_content = ImageValidationWithSlideContent(
            validation_feedback=validation_result,
            tested_slide_content=content
        )
        
        fixed_content, input_tokens, output_tokens = call_image_fixer_agent(validation_with_content)
        
        return {
            "fixed_content": json.loads(fixed_content.model_dump_json()),
            "tokens": {
                "input": input_tokens,
                "output": output_tokens,
                "total": input_tokens + output_tokens
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))





@app.get("/presentation/{presentation_id}", response_model=Dict[str, Any])
async def get_presentation_status(
    request: Request,
    presentation_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(auth_middleware.check_auth),
    db: Session = Depends(get_db)
):
    """Get the status or result of a presentation generation job"""
    client_info = request.state.client_info
    
    if presentation_id not in presentations:
        raise HTTPException(status_code=404, detail="Presentation not found")
    
    presentation = presentations[presentation_id]
    
    response = {
        "presentation_id": presentation_id,
        "status": presentation["status"],
        "progress": presentation.get("progress")
    }
    
    # Include full data if completed
    if presentation["status"] == "completed":
        response["data"] = presentation["data"]
    
    # Include error if failed
    if presentation["status"] == "error":
        response["error"] = presentation.get("error")
    
    return response

@app.get("/presentations", response_model=List[Dict[str, Any]])
async def list_presentations(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(auth_middleware.check_auth),
    db: Session = Depends(get_db),
    skip: int = 0, 
    limit: int = 100
):
    """List all presentations for the authenticated client"""
    client_info = request.state.client_info
    client_id = client_info.client_id if client_info else "anonymous"
    
    # Get presentations from the database
    db_presentations = crud.get_presentations_for_client(db, client_id, skip, limit)
    
    # Combine with in-memory presentations
    combined_presentations = [
        {
            "presentation_id": p.presentation_id,
            "status": presentations.get(p.presentation_id, {}).get("status", "unknown"),
            "title": presentations.get(p.presentation_id, {}).get("data", {}).get("title", p.topic),
            "topic": p.topic,
            "slide_count": p.slide_count,
            "total_tokens": p.total_tokens,
            "generation_time": p.generation_time,
            "created_on": p.created_on.isoformat() if hasattr(p.created_on, 'isoformat') else p.created_on
        }
        for p in db_presentations
    ]
    
    # Add in-memory presentations that might not be in the database yet
    for pid, data in presentations.items():
        if not any(p["presentation_id"] == pid for p in combined_presentations):
            if data.get("request", {}).get("client_id") == client_id:
                combined_presentations.append({
                    "presentation_id": pid,
                    "status": data.get("status", "unknown"),
                    "title": data.get("data", {}).get("title", data.get("request", {}).get("topic", "")),
                    "topic": data.get("request", {}).get("topic", ""),
                    "slide_count": data.get("request", {}).get("slide_count", 0),
                    "total_tokens": data.get("data", {}).get("tokens_used", 0),
                    "generation_time": 0,  # No generation time for in-memory only presentations
                    "created_on": data.get("creation_time", datetime.now().isoformat())
                })
    
    return combined_presentations


@app.get("/presentation-complete/{presentation_id}", response_model=schemas.PresentationResponseSchema)
async def get_complete_presentation(
    request: Request,
    presentation_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(auth_middleware.check_auth),
    db: Session = Depends(get_db)
):
    """Get the complete presentation with all slides"""
    client_info = request.state.client_info
    client_id = client_info.client_id if client_info else "anonymous"
    
    # Get the presentation from the database
    db_presentation = crud.get_presentation_history(db, presentation_id)
    if not db_presentation:
        raise HTTPException(status_code=404, detail="Presentation not found")
    
    # Check if the presentation belongs to the authenticated client
    if db_presentation.client_id != client_id and client_id != "admin":
        raise HTTPException(status_code=403, detail="You don't have permission to access this presentation")
    
    # Get all slides for the presentation
    slides = crud.get_slides_for_presentation(db, presentation_id)
    
    # Create the response model
    slide_responses = []
    for slide in slides:
        slide_response = schemas.SlideResponseSchema(
            slide_number=slide.slide_number,
            slide_title=slide.slide_title,
            slide_focus=slide.slide_focus,
            onscreen_text=slide.onscreen_text,
            voiceover_text=slide.voiceover_text,
            image_prompt=slide.image_prompt,
            image_url=slide.image_url
        )
        slide_responses.append(slide_response)
    
    # Create the presentation response
    presentation_response = schemas.PresentationResponseSchema(
        presentation_id=db_presentation.presentation_id,
        topic=db_presentation.topic,
        slide_count=db_presentation.slide_count,
        total_tokens=db_presentation.total_tokens,
        generation_time=db_presentation.generation_time,
        created_on=db_presentation.created_on,
        slides=slide_responses
    )
    
    return presentation_response


@app.get("/voice-settings/{voice_setting_id}", response_model=Dict[str, Any])
async def get_voice_setting(
    request: Request,
    voice_setting_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(auth_middleware.check_auth),
    db: Session = Depends(get_db)
):
    """Get a specific voice setting by ID"""

    from data.db.schemas import VOICE_SETTINGS
    print(f"Fetching voice setting with ID: {voice_setting_id}")    
    try:
        print("1")
        voice_setting = crud.get_voice_setting(db, voice_setting_id)
        voice_setting = VOICE_SETTINGS.model_validate(voice_setting)


        print("2")
        print(f"Voice setting fetched: {voice_setting}")
        if not voice_setting:
            raise HTTPException(status_code=404, detail="Voice setting not found")
        
        return {
            "status": "success",
            "data": voice_setting.elevenlabs_voice_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


