from pydantic import BaseModel, Field
from typing import List


class Credentials(BaseModel):
    client_id: str
    client_secret: str

class CredentialsCheckResult(BaseModel):
    is_valid: bool
    message: str




class TopicCount(BaseModel):
    presentation_topic: str = Field(description="Topic of the presentation")
    slide_count: int = Field(description="The number of slides that will be generated for this presentation")

class SlideOutline(BaseModel):
    slide_title: str = Field(description="Title of the slide")
    slide_focus: str = Field(description="Core information or message to be conveyed with this particular slide")
    slide_number: int = Field(description="The number of the slide in the presentation")

class PresentationOutline(BaseModel):
    presentation_title: str = Field(description="Title of the presentation")
    slide_outlines: List[SlideOutline] = Field(description="List of slide outlines")

class OutlineValidationResult(BaseModel):
    # is_valid: bool = Field(description="Whether the outline is valid or not")    
    feedback: str = Field(description="Feedback on the outline. This should indicate the slide numbers that need to be improved.")    
    score: int = Field(description="The score of the outline")

class ValidationWithOutline(BaseModel):
    validation_feedback: OutlineValidationResult = Field(description="The result of the outline validation")
    tested_outline: PresentationOutline = Field(description="The tested outline")



class SlideContent(BaseModel):
    slide_onscreen_text: str = Field(description="The textual content with HTML markup that is shown on the slide")
    slide_voiceover_text: str = Field(description="The text for the voiceover of this particular slide")
    slide_image_prompt: str = Field(description="A detailed prompt text to generate an image for this particular slide. This is always in English regardless of the language of the presentation")

class ContentValidationResult(BaseModel):
    # is_valid: bool = Field(description="Whether the content is valid or not")    
    feedback: str = Field(description="Feedback on the content")    
    score: int = Field(description="The score of the content")

class ValidationWithContent(BaseModel):
    validation_feedback: ContentValidationResult = Field(description="The result of the content validation")
    tested_content: SlideContent = Field(description="The tested content")




class RegeneratedPrompt(BaseModel):
    prompt: str = Field(description="The regenerated image prompt")

class ImageValidationResult(BaseModel):
    feedback: str = Field(description="The feedback on the image validation")
    suggestions: str = Field(description="Suggestions for improving the image")
    score: int = Field(description="The score of the image validation")
    # is_valid: bool = Field(description="Whether the image meets quality requirements")   

class ImageValidationWithSlideContent(BaseModel):
    validation_feedback: ImageValidationResult = Field(description="The result of the image validation")
    tested_slide_content: SlideContent = Field(description="The tested slide content")



class SlideExportData(BaseModel):
    slide_onscreen_text: str = Field(description="The textual content with HTML markup that is shown on the slide")
    slide_voiceover_text: str = Field(description="The text for the voiceover of this particular slide")
    slide_image_prompt: str = Field(description="A detailed prompt text to generate an image for this particular slide. This is always in English regardless of the language of the presentation")
    slide_image_url: str = Field(description="The URL of the generated image for this particular slide")