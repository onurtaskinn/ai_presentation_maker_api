# api/app.py
from fastapi import FastAPI
from dotenv import load_dotenv
import os
import json

# Load environment variables
load_dotenv()

# Quality thresholds
OUTLINE_THRESHOLD_SCORE = 0
CONTENT_THRESHOLD_SCORE = 0
IMAGE_THRESHOLD_SCORE = 0
ACCESS_TOKEN_EXPIRE_HOURS = 24

SOURCE_DOCUMENT_DIRECTORY = "source_documents"
MAXIMUM_FILE_SIZE = 10 * 1024 * 1024 # 10MB
MAXIMUM_TEXT_LENGTH = 80000 # 80000 characters
MINIMUM_TEXT_LENGTH = 3500 # 3500 characters



# Mapping for image quality to model
IMAGE_QUALITY_MODELS = {
    "low": "fal-ai/flux/dev",
    "medium": "fal-ai/recraft-20b",
    "high": "fal-ai/imagen3"
}

# In-memory storage for presentations
presentations = {}

# Create FastAPI app
app = FastAPI(
    title="AI Presentation Generator API",
    description="API for generating professional presentations with AI",
    version="1.0.0"
)

# Helper function to save presentation
def save_presentation(presentation_data, presentation_id):
    os.makedirs("_outputs", exist_ok=True)
    filepath = os.path.join("_outputs", f"presentation_{presentation_id}.json")
    
    with open(filepath, "w") as f:
        json.dump(presentation_data, f, indent=2)
    
    return filepath