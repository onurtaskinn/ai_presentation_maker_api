# data/db/models.py
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from data.db.database import Base
from datetime import datetime, timezone

class CLIENT_INFORMATION(Base):
    __tablename__ = 'CLIENT_INFORMATION'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), nullable=True)
    client_id = Column(String(512), nullable=False)
    client_secret = Column(String(512), nullable=False)
    callback_url = Column(String, nullable=True)
    scope = Column(Integer, nullable=True)
    status = Column(Integer, nullable=True)

class PRESENTATION_HISTORY(Base):
    __tablename__ = 'PRESENTATION_HISTORY'
    id = Column(Integer, primary_key=True)
    presentation_id = Column(String(50), unique=True, index=True)
    topic = Column(String(255))
    client_id = Column(String(512))
    slide_count = Column(Integer)
    total_tokens = Column(Integer)
    generation_time = Column(Float)
    created_on = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Define the relationship with PRESENTATION_SLIDES
    slides = relationship("PRESENTATION_SLIDES", back_populates="presentation", cascade="all, delete-orphan")

class PRESENTATION_SLIDES(Base):
    __tablename__ = 'PRESENTATION_SLIDES'
    id = Column(Integer, primary_key=True)
    presentation_id = Column(String(50), ForeignKey("PRESENTATION_HISTORY.presentation_id"), index=True)
    slide_number = Column(Integer)
    slide_title = Column(String(255))
    slide_focus = Column(String(512))
    onscreen_text = Column(Text)
    voiceover_text = Column(Text)
    image_prompt = Column(Text)
    image_url = Column(String(1024))
    
    # Define the relationship with PRESENTATION_HISTORY
    presentation = relationship("PRESENTATION_HISTORY", back_populates="slides")



class PS_VOICES(Base):
    __tablename__ = 'PS_VOICES'
    id = Column(Integer, primary_key=True, index=True)
    personality_id = Column(Integer, ForeignKey('PS_PERSONALITY_TYPES.id'))
    elevenlabs_voice_name = Column(String(500))
    elevenlabs_voice_id = Column(String(500))
    elevenlabs_tts_model = Column(String(100))
    elevenlabs_voice_description = Column(String)
    voice_speed = Column(Float)
    voice_stability = Column(Float)
    voice_similarity = Column(Float)
    status = Column(Integer)
    created_on = Column(DateTime, default=lambda: datetime.now(timezone.utc))
