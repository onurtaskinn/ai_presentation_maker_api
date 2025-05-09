# fastapi_main.py
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import os
import json
from dotenv import load_dotenv
import uuid
from datetime import datetime, timedelta, timezone
import time

# Import datamodels
from data.datamodels import (
    TopicCount, SlideOutline, PresentationOutline, 
    SlideContent, ContentValidationResult, OutlineValidationResult,
    ImageValidationResult, ValidationWithOutline, ImageValidationWithSlideContent,
    Credentials, CredentialsCheckResult
)

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

# Import auth middleware
from app.auth_middleware import auth_middleware, get_db
from app.auth_helper import check_credentials, create_access_token
from data.db import crud, schemas
from sqlalchemy.orm import Session

# Load environment variables
load_dotenv()

# Quality thresholds
OUTLINE_THRESHOLD_SCORE = 0
CONTENT_THRESHOLD_SCORE = 0
IMAGE_THRESHOLD_SCORE = 0
ACCESS_TOKEN_EXPIRE_HOURS = 24

# Create FastAPI app
app = FastAPI(
    title="AI Presentation Generator API",
    description="API for generating professional presentations with AI",
    version="1.0.0"
)

# In-memory storage for presentations
presentations = {}

# Request/Response Models
class TopicRequest(BaseModel):
    topic: str = Field(..., description="Topic of the presentation")
    slide_count: int = Field(..., ge=2, le=15, description="Number of slides")

class OutlineRequest(BaseModel):
    topic: str = Field(..., description="Topic of the presentation")
    slide_count: int = Field(..., ge=2, le=15, description="Number of slides")

class ContentRequest(BaseModel):
    presentation_title: str = Field(..., description="Title of the presentation")
    slide: SlideOutline = Field(..., description="Slide outline information")

class ImageRequest(BaseModel):
    image_prompt: str = Field(..., description="Prompt for image generation")
    quality: str = Field("medium", description="Image quality (low, medium, high)")

class FullPresentationRequest(BaseModel):
    topic: str = Field(..., description="Topic of the presentation")
    slide_count: int = Field(..., ge=2, le=15, description="Number of slides")
    image_quality: str = Field("medium", description="Image quality (low, medium, high)")
    is_agentic: bool = Field(False, description="Whether the presentation is agentic")
    organization_code: Optional[str] = Field(None, description="Organization code")

class PresentationStatusResponse(BaseModel):
    presentation_id: str
    status: str
    progress: Optional[Dict[str, Any]] = None

# Mapping for image quality to model
IMAGE_QUALITY_MODELS = {
    "low": "fal-ai/recraft-20b",
    "medium": "fal-ai/imagen3",
    "high": "fal-ai/flux-pro/v1.1"
}

# Helper function to save presentation
def save_presentation(presentation_data, presentation_id):
    os.makedirs("_outputs", exist_ok=True)
    filepath = os.path.join("_outputs", f"presentation_{presentation_id}.json")
    
    with open(filepath, "w") as f:
        json.dump(presentation_data, f, indent=2)
    
    return filepath

# Authentication endpoint
@app.post("/get_token")
async def get_token(credentials: Credentials, db: Session = Depends(get_db)):
    """
    Generate authentication token for API access.

    - **credentials**: Client credentials (client_id and client_secret)
    """
    if not auth_middleware.require_auth:
        # If auth is not required, return a dummy token
        return {
            "access_token": "dummy_token_for_testing",
            "token_type": "bearer"
        }
    
    credentials_check_result = check_credentials(credentials, db)

    if credentials_check_result.is_valid:
        access_token_expires = timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
        access_token = create_access_token(
            data={"sub": credentials.client_id}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
    else:
        raise HTTPException(status_code=401, detail=credentials_check_result.message)

# Endpoints
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

async def generate_full_presentation_task(presentation_id: str, topic: str, slide_count: int, image_quality: str, is_agentic: bool, client_id: str, organization_code: str = None, db: Session = None):
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

@app.post("/generate-presentation", response_model=PresentationStatusResponse)
async def generate_presentation(
    request: Request,
    presentation_req: FullPresentationRequest, 
    background_tasks: BackgroundTasks,
    credentials: HTTPAuthorizationCredentials = Depends(auth_middleware.check_auth),
    db: Session = Depends(get_db)
):
    """Start generating a complete presentation asynchronously"""
    client_info = request.state.client_info
    client_id = client_info.client_id if client_info else "anonymous"
    
    presentation_id = str(uuid.uuid4())
    
    # Initialize presentation in storage
    presentations[presentation_id] = {
        "status": "queued",
        "creation_time": datetime.now().isoformat(),
        "request": {
            "topic": presentation_req.topic,
            "slide_count": presentation_req.slide_count,
            "image_quality": presentation_req.image_quality,
            "is_agentic": presentation_req.is_agentic,
            "organization_code": presentation_req.organization_code
        }
    }
    
    # Start background task
    background_tasks.add_task(
        generate_full_presentation_task,
        presentation_id=presentation_id,
        topic=presentation_req.topic,
        slide_count=presentation_req.slide_count,
        image_quality=presentation_req.image_quality,
        is_agentic=presentation_req.is_agentic,
        client_id=client_id,
        organization_code=presentation_req.organization_code,
        db=db
    )
    
    return PresentationStatusResponse(
        presentation_id=presentation_id,
        status="queued"
    )

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




if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)