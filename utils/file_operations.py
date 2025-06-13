import fitz
import os
import docx2txt

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