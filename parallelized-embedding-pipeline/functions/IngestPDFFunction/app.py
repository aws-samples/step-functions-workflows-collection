import boto3
import urllib.parse
import os
import tempfile
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List
from io import BytesIO
from PyPDF2 import PdfReader
from pdf2image import convert_from_bytes
from PIL import Image

# Add parent directory to Python path to find shared modules
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent / 'shared' / 'lib'))
from shared.secure_xml import parse_xml, create_safe_parser
from shared.secure_subprocess import run_subprocess_safely  # For safer subprocess operations

s3 = boto3.client('s3')

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def process_pdf(pdf_data: bytes, output_format: str = 'png') -> List[Dict[str, Any]]:
    """
    Process a PDF file securely, extracting text and optionally converting pages to images.
    
    :param pdf_data: The binary PDF data to process
    :param output_format: The output format for page images ('png' or 'jpeg')
    :return: A list of dictionaries containing page information and paths
    """
    # Create secure parser for any XML content in PDF
    secure_parser = create_safe_parser()
    
    results = []
    try:
        pdf_reader = PdfReader(BytesIO(pdf_data))
        # Process each page
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            
            # Extract text content
            text = page.extract_text()
            
            # Convert page to image if needed
            images = []
            if output_format:
                images = convert_from_bytes(
                    pdf_data,
                    first_page=page_num + 1,
                    last_page=page_num + 1,
                    fmt=output_format
                )
                
                if images:
                    # Process any XML metadata in images securely
                    for img in images:
                        if hasattr(img, 'info') and img.info.get('XML:com.adobe.xmp'):
                            try:
                                xml_data = img.info['XML:com.adobe.xmp']
                                metadata = parse_xml(xml_data, forbid_dtd=True, forbid_entities=True)
                                # Store validated metadata if needed
                                logger.info(f"Successfully parsed metadata for page {page_num + 1}")
                            except ValueError as e:
                                logger.warning(f"Failed to parse image metadata for page {page_num + 1}: {e}")
            
            results.append({
                'page_number': page_num + 1,
                'text': text,
                'image_paths': [img.filename for img in images]
            })
            
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        raise
        
    return results

def lambda_handler(event, context):
    bucket = event['Bucket']
    source_key = event['SourceKey'].replace("+", " ")


    try:
        # Download the PDF file from S3
        response = s3.get_object(Bucket=bucket, Key=source_key)
        pdf_content = response['Body'].read()

        # Create a temporary file from the PDF content
        with tempfile.TemporaryFile() as temp_file:
            temp_file.write(pdf_content)
            temp_file.seek(0)  # Move the file pointer to the beginning

            # Extract text from the PDF file
            pdf_reader = PdfReader(temp_file)
            text = ''
            for page in range(len(pdf_reader.pages)):
                text += pdf_reader.pages[page].extract_text()

        # Remove the 'raw/' prefix from the object key
        object_name = os.path.basename(source_key)

        # Write the text to a text file in the 'stage' prefix
        next_key = os.path.join(os.environ['NextPrefix'], object_name + "_text.txt")
        s3.put_object(Bucket=bucket, Key=next_key, Body=text.encode('utf-16'))

        print(f"Text extracted from PDF and written to {next_key} in bucket {bucket}")
    except Exception as e:
        print(f"Error: {e}")
        raise e

    return {
        'statusCode': 200,
        'body': f'File {source_key} processed and written to {next_key}',
        'SourceKey': next_key,
        'Bucket': bucket
    }