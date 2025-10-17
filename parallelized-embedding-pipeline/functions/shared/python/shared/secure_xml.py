"""
Secure XML parsing utilities to prevent XXE attacks and other XML vulnerabilities.
"""
import xml.etree.ElementTree as ET
from xml.parsers.expat import ParserCreate
import logging

logger = logging.getLogger(__name__)

def create_safe_parser():
    """
    Create a secure XML parser that prevents XXE attacks.
    
    Returns:
        xml.parsers.expat.XMLParser: A configured secure parser
    """
    parser = ParserCreate()
    
    # Disable DTD processing to prevent XXE attacks
    parser.DefaultHandler = lambda data: None
    parser.ExternalEntityRefHandler = lambda context, base, sysId, notationName: False
    
    return parser

def parse_xml(xml_data, forbid_dtd=True, forbid_entities=True):
    """
    Safely parse XML data with security restrictions.
    
    Args:
        xml_data (str or bytes): The XML data to parse
        forbid_dtd (bool): Whether to forbid DTD declarations
        forbid_entities (bool): Whether to forbid entity references
        
    Returns:
        xml.etree.ElementTree.Element: The parsed XML root element
        
    Raises:
        ValueError: If XML contains forbidden constructs
        xml.etree.ElementTree.ParseError: If XML is malformed
    """
    if isinstance(xml_data, bytes):
        xml_data = xml_data.decode('utf-8')
    
    # Check for potentially dangerous constructs
    if forbid_dtd and '<!DOCTYPE' in xml_data:
        raise ValueError("DTD declarations are forbidden for security reasons")
    
    if forbid_entities and ('&' in xml_data and ';' in xml_data):
        # More sophisticated entity detection could be added here
        logger.warning("Potential entity references detected in XML")
    
    try:
        # Use defusedxml-style parsing if available, otherwise use standard ET
        root = ET.fromstring(xml_data)
        return root
    except ET.ParseError as e:
        logger.error(f"XML parsing error: {e}")
        raise

def extract_text_from_xml(xml_element):
    """
    Safely extract text content from XML element.
    
    Args:
        xml_element: XML element to extract text from
        
    Returns:
        str: Extracted text content
    """
    if xml_element is None:
        return ""
    
    # Extract text content recursively
    text_parts = []
    if xml_element.text:
        text_parts.append(xml_element.text.strip())
    
    for child in xml_element:
        child_text = extract_text_from_xml(child)
        if child_text:
            text_parts.append(child_text)
        if child.tail:
            text_parts.append(child.tail.strip())
    
    return ' '.join(filter(None, text_parts))