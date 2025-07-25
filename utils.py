import hashlib
import json
import logging
import os
from datetime import datetime


def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def validate_pdf_file(file_path):
    """Validate if a file is a valid PDF with proper content validation"""
    if not os.path.exists(file_path):
        return False, "File does not exist"

    # Check file extension first
    if not file_path.lower().endswith(".pdf"):
        return False, "File is not a PDF"

    # Check PDF magic bytes (proper validation)
    try:
        with open(file_path, "rb") as f:
            header = f.read(8)
            if not header.startswith(b"%PDF-"):
                return False, "File is not a valid PDF (invalid header)"

        # Try to open with PyPDF2 as additional validation
        import PyPDF2

        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            # Try to access pages to ensure it's a valid PDF
            len(reader.pages)

        return True, "Valid PDF file"

    except Exception as e:
        return False, f"Invalid PDF file: {str(e)}"


def calculate_file_hash(file_path):
    """Calculate SHA-256 hash of a file with proper error handling"""
    try:
        hash_sha256 = hashlib.sha256()

        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)

        return hash_sha256.hexdigest()

    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")
    except PermissionError:
        raise PermissionError(f"Permission denied accessing file: {file_path}")
    except OSError as e:
        raise OSError(f"I/O error reading file {file_path}: {str(e)}")
    except Exception as e:
        raise Exception(f"Unexpected error calculating hash for {file_path}: {str(e)}")


def save_extraction_log(zones, filename):
    """Save extraction results to a log file with data sanitization"""
    try:
        # Sanitize filename to remove potential sensitive path information
        sanitized_filename = os.path.basename(filename) if filename else "unknown"

        # Sanitize zones data - only keep essential information
        sanitized_zones = []
        for zone in zones:
            sanitized_zone = {
                "page": zone.get("page", "unknown"),
                "zone_code": zone.get("zone_code", "unknown"),
                "method": zone.get("method", "unknown"),
            }
            sanitized_zones.append(sanitized_zone)

        log_data = {
            "timestamp": datetime.now().isoformat(),
            "filename": sanitized_filename,
            "zones_count": len(sanitized_zones),
            "zones": sanitized_zones,
        }

        log_filename = f"extraction_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(log_filename, "w") as f:
            json.dump(log_data, f, indent=2)

        return log_filename

    except Exception as e:
        raise Exception(f"Failed to save extraction log: {str(e)}")


def clean_temp_files(max_age_hours=24):
    """Clean up temporary files efficiently and safely"""
    import tempfile
    import time

    try:
        temp_dir = tempfile.gettempdir()
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        cleaned_count = 0

        # Only process files that match our specific pattern and are old enough
        for filename in os.listdir(temp_dir):
            if filename.startswith("tmp") and filename.endswith(".pdf"):
                file_path = os.path.join(temp_dir, filename)
                try:
                    # Check file age before deletion
                    file_age = current_time - os.path.getmtime(file_path)
                    if file_age > max_age_seconds:
                        os.remove(file_path)
                        cleaned_count += 1
                except OSError:
                    # File might be in use or already deleted
                    continue

        return cleaned_count

    except Exception as e:
        raise Exception(f"Failed to clean temp files: {str(e)}")


def format_zone_code(zone_code):
    """Format zone code consistently with input validation"""
    if not zone_code:
        return ""

    # Input validation and type safety
    if not isinstance(zone_code, (str, int, float)):
        raise TypeError(f"zone_code must be string, int, or float, got {type(zone_code)}")

    # Convert to string and format
    zone_str = str(zone_code).strip()
    if not zone_str:
        return ""

    return zone_str.upper()


def get_pdf_metadata(file_path):
    """Extract basic metadata from PDF with proper error handling"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    try:
        import PyPDF2

        with open(file_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)

            metadata = {
                "pages": len(reader.pages),
                "title": "Unknown",
                "author": "Unknown",
                "subject": "Unknown",
                "creator": "Unknown",
                "producer": "Unknown",
            }

            # Safely extract metadata if available
            if reader.metadata:
                metadata.update(
                    {
                        "title": reader.metadata.get("/Title", "Unknown") or "Unknown",
                        "author": reader.metadata.get("/Author", "Unknown") or "Unknown",
                        "subject": reader.metadata.get("/Subject", "Unknown") or "Unknown",
                        "creator": reader.metadata.get("/Creator", "Unknown") or "Unknown",
                        "producer": reader.metadata.get("/Producer", "Unknown") or "Unknown",
                    }
                )

            return metadata

    except ImportError:
        raise ImportError("PyPDF2 is required for PDF metadata extraction")
    except Exception as e:
        # Check if it's a PyPDF2 specific error
        if "PyPDF2" in str(type(e)):
            raise ValueError(f"Invalid or corrupted PDF file: {str(e)}")
        else:
            raise Exception(f"Failed to extract PDF metadata: {str(e)}")
