"""
Common document processing utilities.
"""
import re
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

def clean_text(text: str) -> str:
    """
    Clean and normalize text content.
    
    Args:
        text: Raw text to clean
        
    Returns:
        str: Cleaned text
    """
    if not text:
        return ""
    
    # Remove null bytes that cause PostgreSQL UTF-8 encoding errors
    text = text.replace('\x00', '')
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove excessive line breaks
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
    
    return text.strip()

def detect_document_type(filename: str) -> Tuple[str, str]:
    """
    Detect document type from filename.
    
    Args:
        filename: The filename to analyze
        
    Returns:
        Tuple[str, str]: (document_type, document_sub_type)
    """
    filename_lower = filename.lower()
    
    # Default type
    doc_type = "Text"
    doc_subtype = "Text"
    
    # Check for document types based on extensions
    if filename_lower.endswith('.pdf'):
        doc_type = "PDF"
        doc_subtype = "PDF"
    elif filename_lower.endswith(('.doc', '.docx')):
        doc_type = "DOCX"
        doc_subtype = "DOCX"
    elif filename_lower.endswith(('.ppt', '.pptx')):
        doc_type = "PPT"
        doc_subtype = "PPT"
    elif filename_lower.endswith(('.xls', '.xlsx')):
        doc_type = "Excel"
        doc_subtype = "Excel"
    elif filename_lower.endswith('.txt'):
        doc_type = "Text"
        doc_subtype = "Text"
    elif filename_lower.endswith(('.html', '.htm')):
        doc_type = "HTML"
        doc_subtype = "HTML"
    elif filename_lower.endswith('.json'):
        doc_type = "JSON"
        doc_subtype = "JSON"
    elif filename_lower.endswith('.xml'):
        doc_type = "XML"
        doc_subtype = "XML"
    elif filename_lower.endswith('.csv'):
        doc_type = "CSV"
        doc_subtype = "CSV"
    
    logger.info(f"Detected document type: {doc_type}, subtype: {doc_subtype} for file: {filename}")
    return doc_type, doc_subtype

def truncate_text(text: str, max_chars: int = 8000) -> str:
    """
    Truncate text to a maximum number of characters.
    
    Args:
        text: Text to truncate
        max_chars: Maximum number of characters
        
    Returns:
        str: Truncated text
    """
    if len(text) <= max_chars:
        return text
    
    logger.warning(f"Text is too long ({len(text)} chars), truncating to {max_chars} chars")
    return text[:max_chars]

def safe_decode(data: bytes, encodings: list = None) -> str:
    """
    Safely decode bytes to string trying multiple encodings.
    
    Args:
        data: Bytes to decode
        encodings: List of encodings to try (default: ['utf-8', 'utf-16', 'utf-16-le', 'latin-1'])
        
    Returns:
        str: Decoded string
    """
    if encodings is None:
        encodings = ['utf-8', 'utf-16', 'utf-16-le', 'latin-1']
    
    for encoding in encodings:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    
    # Last resort - decode with errors='replace'
    logger.warning("Could not decode with any standard encoding, using utf-8 with error replacement")
    return data.decode('utf-8', errors='replace')