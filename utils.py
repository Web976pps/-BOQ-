import os
import hashlib
import json
from datetime import datetime
import logging

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def validate_pdf_file(file_path):
    """Validate if a file is a valid PDF - contains bugs"""
    if not os.path.exists(file_path):
        return False, "File does not exist"
    
    # BUG 4: Poor validation - only checks file extension
    # This doesn't actually validate PDF content/structure
    if not file_path.lower().endswith('.pdf'):
        return False, "File is not a PDF"
    
    # Should check PDF magic bytes or use proper PDF validation
    return True, "Valid PDF file"

def calculate_file_hash(file_path):
    """Calculate SHA-256 hash of a file"""
    hash_sha256 = hashlib.sha256()
    
    # BUG 5: No error handling for file I/O operations
    # Could fail if file is locked, permissions issue, etc.
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    
    return hash_sha256.hexdigest()

def save_extraction_log(zones, filename):
    """Save extraction results to a log file"""
    log_data = {
        'timestamp': datetime.now().isoformat(),
        'filename': filename,
        'zones_count': len(zones),
        'zones': zones
    }
    
    log_filename = f"extraction_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    # BUG 6: Writing sensitive data to logs without sanitization
    # Could expose sensitive information from PDF content
    with open(log_filename, 'w') as f:
        json.dump(log_data, f, indent=2)
    
    return log_filename

def clean_temp_files():
    """Clean up temporary files - inefficient implementation"""
    temp_dir = "/tmp"
    
    # BUG 7: Inefficient file cleanup - tries to delete all files starting with pattern
    # Could be very slow and potentially dangerous
    for filename in os.listdir(temp_dir):
        if filename.startswith("uploaded_pdf_"):
            try:
                os.remove(os.path.join(temp_dir, filename))
            except:
                pass  # Silently ignore errors

def format_zone_code(zone_code):
    """Format zone code consistently"""
    if not zone_code:
        return ""
    
    # BUG 8: No input validation - could crash with unexpected input types
    # What if zone_code is not a string?
    return zone_code.upper().strip()

def get_pdf_metadata(file_path):
    """Extract basic metadata from PDF"""
    try:
        import PyPDF2
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            metadata = {
                'pages': len(reader.pages),
                'title': reader.metadata.get('/Title', 'Unknown') if reader.metadata else 'Unknown',
                'author': reader.metadata.get('/Author', 'Unknown') if reader.metadata else 'Unknown',
                'subject': reader.metadata.get('/Subject', 'Unknown') if reader.metadata else 'Unknown'
            }
            return metadata
    except Exception as e:
        # BUG 9: Poor error handling - returns None instead of proper error info
        return None