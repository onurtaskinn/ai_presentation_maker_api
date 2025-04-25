from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import os
import json
from dotenv import load_dotenv
import uuid
from datetime import datetime

# Import datamodels
from utils.datamodels import (
    TopicCount, SlideOutline, PresentationOutline, 
    SlideContent, ContentValidationResult, OutlineValidationResult,
    ImageValidationResult, ValidationWithOutline, ImageValidationWithSlideContent
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

# Load environment variables
load_dotenv()

# Quality thresholds
OUTLINE_THRESHOLD_SCORE = 0
CONTENT_THRESHOLD_SCORE = 0
IMAGE_THRESHOLD_SCORE = 0

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

# Endpoints
@app.get("/")
def read_root():
    return {"message": "AI Presentation Generator API", "version": "1.0.0"}

@app.post("/generate-outline", response_model=Dict[str, Any])
async def generate_outline(request: OutlineRequest):
    """Generate a presentation outline based on topic and slide count"""
    try:
        topic_count = TopicCount(
            presentation_topic=request.topic,
            slide_count=request.slide_count
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
async def test_outline(request: Dict[str, Any]):
    """Test a presentation outline for quality"""
    try:
        topic_count = TopicCount(
            presentation_topic=request.get("topic"),
            slide_count=len(request.get("outline", {}).get("slide_outlines", []))
        )
        
        outline = PresentationOutline.model_validate(request.get("outline"))
        
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
async def fix_outline(request: Dict[str, Any]):
    """Fix a presentation outline based on test feedback"""
    try:
        # Create ValidationWithOutline from request
        outline = PresentationOutline.model_validate(request.get("outline"))
        
        validation_result = OutlineValidationResult(
            feedback=request.get("feedback", ""),
            score=request.get("score", 0)
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
async def generate_content(request: ContentRequest):
    """Generate content for a slide"""
    try:
        content, input_tokens, output_tokens = call_content_initial_generator_agent(
            request.presentation_title,
            request.slide
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
async def test_content(request: Dict[str, Any]):
    """Test slide content for quality"""
    try:
        presentation_title = request.get("presentation_title", "")
        slide = SlideOutline.model_validate(request.get("slide", {}))
        content = SlideContent.model_validate(request.get("content", {}))
        
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
async def fix_content(request: Dict[str, Any]):
    """Fix slide content based on test feedback"""
    try:
        presentation_title = request.get("presentation_title", "")
        slide = SlideOutline.model_validate(request.get("slide", {}))
        content = SlideContent.model_validate(request.get("content", {}))
        
        validation_result = ContentValidationResult(
            feedback=request.get("feedback", ""),
            score=request.get("score", 0)
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
async def generate_image(request: ImageRequest):
    """Generate an image based on a prompt"""
    try:
        model = IMAGE_QUALITY_MODELS.get(request.quality.lower(), IMAGE_QUALITY_MODELS["medium"])
        
        image_url = call_image_generator_agent(request.image_prompt, model)
        
        return {
            "image_url": image_url,
            "model_used": model
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/test-image", response_model=Dict[str, Any])
async def test_image(request: Dict[str, Any]):
    """Test an image for quality and relevance"""
    try:
        image_url = request.get("image_url", "")
        content = SlideContent.model_validate(request.get("content", {}))
        
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
async def fix_image_prompt(request: Dict[str, Any]):
    """Fix an image prompt based on test feedback"""
    try:
        content = SlideContent.model_validate(request.get("content", {}))
        validation_result = ImageValidationResult.model_validate(request.get("validation_result", {}))
        
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

# Background task for generating full presentations
async def generate_full_presentation_task(presentation_id: str, topic: str, slide_count: int, image_quality: str, is_agentic: bool):

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
                "slides": []
            }
            
            # Model for image generation
            model = IMAGE_QUALITY_MODELS.get(image_quality.lower(), IMAGE_QUALITY_MODELS["medium"])
            
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

                
                # Store slide data
                presentation_data["slides"].append({
                    "number": i+1,
                    "title": slide.slide_title,
                    "focus": slide.slide_focus,
                    "onscreen_text": content.slide_onscreen_text,
                    "voiceover_text": content.slide_voiceover_text,
                    "image_prompt": content.slide_image_prompt,
                    "image_url": image_url
                })
            
            # Update presentation metadata
            presentation_data["tokens_used"] = total_tokens
            
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
                "slides": []
            }
            
            # Model for image generation
            model = IMAGE_QUALITY_MODELS.get(image_quality.lower(), IMAGE_QUALITY_MODELS["medium"])
            
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
                              
                # Generate image
                image_url = call_image_generator_agent(content.slide_image_prompt, model)
                                
                # Store slide data
                presentation_data["slides"].append({
                    "number": i+1,
                    "title": slide.slide_title,
                    "focus": slide.slide_focus,
                    "onscreen_text": content.slide_onscreen_text,
                    "voiceover_text": content.slide_voiceover_text,
                    "image_prompt": content.slide_image_prompt,
                    "image_url": image_url
                })
            
            # Update presentation metadata
            presentation_data["tokens_used"] = total_tokens
            
            # Save presentation to file
            filepath = save_presentation(presentation_data, presentation_id)
            presentations[presentation_id]["filepath"] = filepath
            presentations[presentation_id]["data"] = presentation_data
            presentations[presentation_id]["status"] = "completed"
            presentations[presentation_id]["progress"] = {"completion": 100}
        
        except Exception as e:
            presentations[presentation_id]["status"] = "error"
            presentations[presentation_id]["error"] = str(e)

@app.post("/generate-presentation", response_model=PresentationStatusResponse)
async def generate_presentation(request: FullPresentationRequest, background_tasks: BackgroundTasks):
    """Start generating a complete presentation asynchronously"""
    presentation_id = str(uuid.uuid4())
    
    # Initialize presentation in storage
    presentations[presentation_id] = {
        "status": "queued",
        "creation_time": datetime.now().isoformat(),
        "request": {
            "topic": request.topic,
            "slide_count": request.slide_count,
            "image_quality": request.image_quality,
            "is_agentic": request.is_agentic
        }
    }
    
    # Start background task
    background_tasks.add_task(
        generate_full_presentation_task,
        presentation_id=presentation_id,
        topic=request.topic,
        slide_count=request.slide_count,
        image_quality=request.image_quality,
        is_agentic=request.is_agentic,
    )
    
    return PresentationStatusResponse(
        presentation_id=presentation_id,
        status="queued"
    )

@app.get("/presentation/{presentation_id}", response_model=Dict[str, Any])
async def get_presentation_status(presentation_id: str):
    """Get the status or result of a presentation generation job"""
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
async def list_presentations():
    """List all presentations"""
    return [
        {
            "presentation_id": pid,
            "status": data["status"],
            "title": data.get("data", {}).get("title", ""),
            "creation_time": data["creation_time"]
        }
        for pid, data in presentations.items()
    ]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)