import fitz
import os
import docx2txt
from fastapi import UploadFile, HTTPException
from api.app import MAXIMUM_FILE_SIZE, MINIMUM_TEXT_LENGTH, MAXIMUM_TEXT_LENGTH
from api.app import SOURCE_DOCUMENT_DIRECTORY



OUTPUT_FILE_DIRECTORY = "./source_documents"

def ensure_directory_exists(directory_path: str):
    """Create directory if it doesn't exist"""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

def extract_text_from_docx(docx_path):
    """Extract text from a DOCX file"""
    text = docx2txt.process(docx_path)
    return text

def extract_text_from_pdf(file_path):
    """Extract text from PDF file path"""
    document = fitz.open(file_path)
    full_text = ""
    
    for page in document:
        full_text += page.get_text()
    
    document.close()
    
    return full_text


def allowed_file(filename: str) -> bool:
    """
    Validate that the file has a PDF or Word extension.
    """
    lower_filename = filename.lower()
    return (
        lower_filename.endswith(".pdf") or 
        lower_filename.endswith(".docx") or 
        lower_filename.endswith(".doc")
    )



async def process_uploaded_file(file: UploadFile) -> str:
    """
    Process uploaded file: validate, save, and extract text content.
    
    Args:
        file: FastAPI UploadFile object
        
    Returns:
        str: Extracted text content from the file
        
    Raises:
        HTTPException: For various validation and processing errors
    """
    
    # Validate file type
    if not allowed_file(file.filename):
        raise HTTPException(
            status_code=400,             
            detail={
                "error_code": "PRESENTATION_ERROR_TYPE_3",
                "message": "Invalid file type. Only PDF or Word files are accepted."
            }
        )
    
    # Read file content
    try:
        file_contents = await file.read()    
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail={
                "error_code": "PRESENTATION_ERROR_TYPE_4",
                "message": f"Error reading the file: {str(e)}"
            }
        )

    # Check file size
    if len(file_contents) > MAXIMUM_FILE_SIZE:
        raise HTTPException(
            status_code=400, 
            detail={
                "error_code": "PRESENTATION_ERROR_TYPE_5",
                "message": f"File size exceeds the maximum limit of {MAXIMUM_FILE_SIZE/1024/1024:.1f}MB."
            }
        )     

    # Create uploads directory if it doesn't exist
    ensure_directory_exists(SOURCE_DOCUMENT_DIRECTORY)
    file_path = os.path.join(SOURCE_DOCUMENT_DIRECTORY, file.filename)

    # Save the file
    try:
        with open(file_path, "wb") as f:
            f.write(file_contents)
    except Exception as e:
        raise HTTPException(
            status_code=500,  
            detail={
                "error_code": "PRESENTATION_ERROR_TYPE_6",
                "message": f"Error saving the file: {str(e)}"
            }
        )       
    
    # Extract text from the file based on its type
    try:
        extracted_text = ""
        if file.filename.lower().endswith(('.doc', '.docx')):
            extracted_text = extract_text_from_docx(file_path)
        elif file.filename.lower().endswith('.pdf'):
            extracted_text = extract_text_from_pdf(file_path)
    except Exception as e:
        raise HTTPException(
            status_code=500,  
            detail={
                "error_code": "PRESENTATION_ERROR_TYPE_7",
                "message": f"Error extracting text from file: {str(e)}"
            }
        )
    
    # Check extracted text length
    text_length = len(extracted_text)
    if text_length > MAXIMUM_TEXT_LENGTH:
        raise HTTPException(
            status_code=400, 
            detail={
                "error_code": "PRESENTATION_ERROR_TYPE_8",
                "message": f"Extracted text length ({text_length} characters) exceeds the maximum limit of {MAXIMUM_TEXT_LENGTH} characters."
            }
        )
    
    if text_length < MINIMUM_TEXT_LENGTH:
        raise HTTPException(
            status_code=400, 
            detail={
                "error_code": "PRESENTATION_ERROR_TYPE_9",
                "message": f"Extracted text length ({text_length} characters) is below the minimum requirement of {MINIMUM_TEXT_LENGTH} characters."
            }
        )    

    print(f"Extracted text length: {text_length} characters")
    print(f"Extracted text: {extracted_text[:100]}...")  # Print first 100 characters for debugging
    
    return extracted_text