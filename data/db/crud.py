# data/db/crud.py
from fastapi import HTTPException
from sqlalchemy.orm import Session
from data.db.models import CLIENT_INFORMATION, PRESENTATION_HISTORY, PRESENTATION_SLIDES, PS_VOICES
from data.db import schemas

# CRUD operations for CLIENT_INFORMATION
def get_client_info(db: Session, name: str):
    return db.query(CLIENT_INFORMATION).filter(CLIENT_INFORMATION.name == name).first()

def get_client_info_by_id(db: Session, client_id: str):
    return db.query(CLIENT_INFORMATION).filter(CLIENT_INFORMATION.client_id == client_id).first()

def get_client_info_by_secret(db: Session, client_secret: str):
    return db.query(CLIENT_INFORMATION).filter(CLIENT_INFORMATION.client_secret == client_secret).first()

def create_client_info(db: Session, client_info: schemas.CLIENT_INFORMATIONBase):
    db_client = CLIENT_INFORMATION(**client_info.dict())
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    return db_client

# CRUD operations for PRESENTATION_HISTORY
def get_presentation_history(db: Session, presentation_id: str):
    return db.query(PRESENTATION_HISTORY).filter(PRESENTATION_HISTORY.presentation_id == presentation_id).first()

def get_presentations_for_client(db: Session, client_id: str, skip: int = 0, limit: int = 100):
    return db.query(PRESENTATION_HISTORY).filter(PRESENTATION_HISTORY.client_id == client_id).order_by(PRESENTATION_HISTORY.created_on.desc()).offset(skip).limit(limit).all()

def create_presentation_history(db: Session, presentation: schemas.PRESENTATION_HISTORYCreate):
    db_presentation = PRESENTATION_HISTORY(**presentation.dict())
    db.add(db_presentation)
    db.commit()
    db.refresh(db_presentation)
    return db_presentation

def update_presentation_history(db: Session, presentation_id: str, tokens: int, generation_time: float):
    db_presentation = db.query(PRESENTATION_HISTORY).filter(PRESENTATION_HISTORY.presentation_id == presentation_id).first()
    if db_presentation:
        db_presentation.total_tokens = tokens
        db_presentation.generation_time = generation_time
        db.commit()
        db.refresh(db_presentation)
    return db_presentation

# CRUD operations for PRESENTATION_SLIDES
def get_slides_for_presentation(db: Session, presentation_id: str):
    return db.query(PRESENTATION_SLIDES).filter(PRESENTATION_SLIDES.presentation_id == presentation_id).order_by(PRESENTATION_SLIDES.slide_number).all()

def get_slide_by_number(db: Session, presentation_id: str, slide_number: int):
    return db.query(PRESENTATION_SLIDES).filter(
        PRESENTATION_SLIDES.presentation_id == presentation_id,
        PRESENTATION_SLIDES.slide_number == slide_number
    ).first()

def create_presentation_slide(db: Session, slide: schemas.PRESENTATION_SLIDESCreate):
    db_slide = PRESENTATION_SLIDES(**slide.model_dump())
    db.add(db_slide)
    db.commit()
    db.refresh(db_slide)
    return db_slide

def create_presentation_slides_batch(db: Session, slides: list[schemas.PRESENTATION_SLIDESCreate]):
    db_slides = []
    for slide_data in slides:
        db_slide = PRESENTATION_SLIDES(**slide_data.model_dump())
        db.add(db_slide)
        db_slides.append(db_slide)
    db.commit()
    for slide in db_slides:
        db.refresh(slide)
    return db_slides

def update_presentation_slide(db: Session, slide_id: int, slide_update: dict):
    db_slide = db.query(PRESENTATION_SLIDES).filter(PRESENTATION_SLIDES.id == slide_id).first()
    if not db_slide:
        raise HTTPException(status_code=404, detail="Slide not found")
    
    for key, value in slide_update.items():
        setattr(db_slide, key, value)
    
    db.commit()
    db.refresh(db_slide)
    return db_slide

def delete_presentation_slide(db: Session, slide_id: int):
    db_slide = db.query(PRESENTATION_SLIDES).filter(PRESENTATION_SLIDES.id == slide_id).first()
    if db_slide:
        db.delete(db_slide)
        db.commit()
        return True
    return False

def delete_all_slides_for_presentation(db: Session, presentation_id: str):
    db.query(PRESENTATION_SLIDES).filter(
        PRESENTATION_SLIDES.presentation_id == presentation_id
    ).delete(synchronize_session=False)
    db.commit()
    return True

def get_full_presentation_with_slides(db: Session, presentation_id: str):
    presentation = db.query(PRESENTATION_HISTORY).filter(
        PRESENTATION_HISTORY.presentation_id == presentation_id
    ).first()
    
    if not presentation:
        return None
    
    slides = db.query(PRESENTATION_SLIDES).filter(
        PRESENTATION_SLIDES.presentation_id == presentation_id
    ).order_by(PRESENTATION_SLIDES.slide_number).all()
    
    # Construct the full presentation response
    presentation_data = schemas.PRESENTATION_HISTORY.from_orm(presentation)
    presentation_data.slides = [schemas.PRESENTATION_SLIDES.from_orm(slide) for slide in slides]
    
    return presentation_data


# CRUD operations for PS_VOICES

def get_voice_setting(db: Session, voice_setting_id: int):
    return db.query(PS_VOICES).filter(PS_VOICES.id == voice_setting_id).first()