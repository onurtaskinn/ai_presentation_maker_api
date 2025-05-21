# data/db/schemas.py
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional, List

model_config = ConfigDict(
    protected_namespaces=(),
    from_attributes=True
)

# Client Information Schemas
class CLIENT_INFORMATIONBase(BaseModel):
    name: str
    client_id: str
    client_secret: str
    callback_url: Optional[str] = None
    scope: Optional[int] = None
    status: Optional[int] = None

class CLIENT_INFORMATION(CLIENT_INFORMATIONBase):
    id: int
    model_config = model_config

# Presentation Slide Schemas
class PRESENTATION_SLIDESBase(BaseModel):
    presentation_id: str
    slide_number: int
    slide_title: str
    slide_focus: str
    onscreen_text: str
    voiceover_text: str
    image_prompt: str
    image_url: str

class PRESENTATION_SLIDESCreate(PRESENTATION_SLIDESBase):
    pass

class PRESENTATION_SLIDES(PRESENTATION_SLIDESBase):
    id: int
    
    model_config = model_config

# Presentation History Schemas
class PRESENTATION_HISTORYBase(BaseModel):
    presentation_id: str
    topic: str
    client_id: str
    slide_count: int
    total_tokens: Optional[int] = None
    generation_time: Optional[float] = None
    created_on: datetime

class PRESENTATION_HISTORYCreate(PRESENTATION_HISTORYBase):
    pass

class PRESENTATION_HISTORY(PRESENTATION_HISTORYBase):
    id: int
    slides: List[PRESENTATION_SLIDES] = []
    
    model_config = model_config

# Slide Response Schema for API
class SlideResponseSchema(BaseModel):
    slide_number: int
    slide_title: str
    slide_focus: str
    onscreen_text: str
    voiceover_text: str
    image_prompt: str
    image_url: str
    
    model_config = model_config

# Presentation Response Schema for API
class PresentationResponseSchema(BaseModel):
    presentation_id: str
    topic: str
    slide_count: int
    total_tokens: Optional[int] = None
    generation_time: Optional[float] = None
    created_on: datetime
    slides: List[SlideResponseSchema] = []
    
    model_config = model_config


# Voice Settings Schemas


class VOICE_SETTINGS(BaseModel):
    id: int
    personality_id: int
    elevenlabs_voice_name: str
    elevenlabs_voice_id: str
    elevenlabs_tts_model: str
    elevenlabs_voice_description: Optional[str] = None
    voice_speed: float = 1.0
    voice_stability: float = 0.5
    voice_similarity: float = 0.75
    status: int = 1
    created_on: datetime    
    
    model_config = model_config
