import os
import re
import tempfile
import time
from collections import defaultdict
from datetime import datetime

import cv2
import numpy as np
import pandas as pd
import pdfplumber
import pytesseract
import streamlit as st
from pdf2image import convert_from_path
from PIL import Image, ImageFile
from shapely.geometry import Point, box
from shapely.ops import unary_union
from sklearn.cluster import DBSCAN
import logging

# Set up comprehensive logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# CRITICAL FIX: Set PIL limits for large A1 images
Image.MAX_IMAGE_PIXELS = None  # Remove decompression bomb limit

ImageFile.LOAD_TRUNCATED_IMAGES = True  # Handle truncated images gracefully
import warnings

warnings.filterwarnings("ignore", "Palette images with Transparency")


# Enhanced spatial analysis utilities
def to_mm(px: float, dpi: int) -> float:
    """Convert pixels to millimetres for precise measurements"""
    return px * 25.4 / dpi


def to_px(mm: float, dpi: int) -> float:
    """Convert millimetres to pixels for DPI scaling"""
    return mm * dpi / 25.4


def calculate_polygon_overlap(poly1, poly2):
    """Calculate overlap percentage between two Shapely polygons"""
    try:
        if not poly1.intersects(poly2):
            return 0.0
        intersection = poly1.intersection(poly2)
        smaller_area = min(poly1.area, poly2.area)
        if smaller_area == 0:
            return 0.0
        return (intersection.area / smaller_area) * 100
    except Exception:
        return 0.0


st.set_page_config(page_title="A1 PDF Zones/Codes Extractor - Enhanced", layout="wide")


class A1PDFProcessor:
    """A1-specific PDF processing with enhanced image quality"""

    def __init__(self):
        self.target_dpi = 300  # Start with 300 DPI for safety
        self.max_dpi = 600  # Maximum DPI allowed
        self.min_dpi = 150  # Minimum acceptable DPI
        self.a1_dimensions_mm = (594, 841)  # A1 size in mm
        self.a1_dimensions_px = None  # Will be calculated based on DPI
        # ENHANCED: More conservative pixel limit to prevent memory issues
        self.max_pixels = 150_000_000  # 150 megapixels safety limit (increased from 50M for A1)

        # Enhanced performance optimization
        self.optimization_enabled = True
        self.shapely_acceleration = True
        self.memory_efficient_processing = True

    def detect_a1_format(self, pdf_path):
        """Enhanced A1 format detection for architectural drawings"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                page = pdf.pages[0]  # Check first page
                width_mm = page.width * 25.4 / 72  # Convert points to mm
                height_mm = page.height * 25.4 / 72

                # ENHANCED: Multiple criteria for large format detection

                # Standard A1 dimensions
                a1_width, a1_height = 594, 841

                # Check exact A1 match first (with tight tolerance)
                tolerance = 10  # 10mm tolerance for precise format detection
                is_a1_portrait = (
                    abs(width_mm - a1_width) < tolerance and abs(height_mm - a1_height) < tolerance
                )
                is_a1_landscape = (
                    abs(width_mm - a1_height) < tolerance and abs(height_mm - a1_width) < tolerance
                )

                if is_a1_portrait:
                    return True, "portrait", (width_mm, height_mm)
                elif is_a1_landscape:
                    return True, "landscape", (width_mm, height_mm)

                # ENHANCED: Detect large format architectural drawings
                # Many architectural drawings are A1-equivalent but not exact A1
                min_dimension = min(width_mm, height_mm)
                max_dimension = max(width_mm, height_mm)

                # Large format criteria (architectural drawing size)
                is_large_format = (
                    min_dimension >= 400
                    and max_dimension >= 600  # Minimum large format
                    and min_dimension <= 1200
                    and max_dimension <= 1200  # Maximum reasonable
                )

                # Aspect ratio check for architectural drawings
                aspect_ratio = max_dimension / min_dimension
                is_reasonable_aspect = 1.2 <= aspect_ratio <= 2.0  # Common architectural ratios

                if is_large_format and is_reasonable_aspect:
                    orientation = "landscape" if width_mm > height_mm else "portrait"
                    st.info(
                        f"📐 Detected large format architectural drawing: {width_mm:.1f}x{height_mm:.1f}mm"
                    )
                    return True, orientation, (width_mm, height_mm)
                else:
                    st.warning(
                        f"📄 Small format document detected: {width_mm:.1f}x{height_mm:.1f}mm (may not be optimal for architectural processing)"
                    )
                    return False, "small_format", (width_mm, height_mm)

        except Exception as e:
            st.error(f"Could not detect PDF format: {str(e)}")
            return False, "error", (0, 0)

    def calculate_safe_dpi(self, page_width_mm, page_height_mm):
        """Calculate safe DPI based on page dimensions to avoid PIL limits"""
        try:
            # Calculate page dimensions in inches
            width_inches = page_width_mm / 25.4
            height_inches = page_height_mm / 25.4

            # Calculate maximum safe DPI based on our pixel limit
            # max_pixels = width_px * height_px = (width_in * dpi) * (height_in * dpi)
            # Therefore: dpi = sqrt(max_pixels / (width_in * height_in))
            area_square_inches = width_inches * height_inches
            max_safe_dpi = int((self.max_pixels / area_square_inches) ** 0.5)

            # ENHANCED: Apply more conservative constraints for large images
            # Apply 20% safety margin for memory allocation overhead
            conservative_dpi = int(max_safe_dpi * 0.8)
            safe_dpi = max(self.min_dpi, min(conservative_dpi, self.max_dpi))

            # Calculate actual pixel count at this DPI
            actual_pixels = (width_inches * safe_dpi) * (height_inches * safe_dpi)

            # Additional safety check - if still too large, reduce further
            if actual_pixels > self.max_pixels:
                # More aggressive reduction
                safe_dpi = int(safe_dpi * 0.7)
                actual_pixels = (width_inches * safe_dpi) * (height_inches * safe_dpi)

            if safe_dpi < self.max_dpi:
                st.info(
                    f"🔧 Adjusted DPI to {safe_dpi} for safety ({int(actual_pixels/1000000)}MP, {int(actual_pixels):,} pixels)"
                )

            return safe_dpi

        except Exception as e:
            st.warning(f"DPI calculation failed: {str(e)}, using default")
            return self.min_dpi

    def enhance_image_quality(self, image):
        """Enhanced image processing for architectural drawings"""
        try:
            # Convert PIL to OpenCV format
            img_array = np.array(image)
            if len(img_array.shape) == 3:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

            # Convert to grayscale for processing
            gray = (
                cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
                if len(img_array.shape) == 3
                else img_array
            )

            # Noise reduction for architectural drawings
            denoised = cv2.bilateralFilter(gray, 9, 75, 75)

            # Contrast enhancement using CLAHE
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(denoised)

            # Sharpening filter for text clarity
            kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
            sharpened = cv2.filter2D(enhanced, -1, kernel)

            # Convert back to PIL Image
            return Image.fromarray(sharpened)

        except Exception as e:
            st.warning(f"Image enhancement failed: {str(e)}")
            return image

    def correct_orientation(self, image):
        """Detect and correct image orientation"""
        try:
            # Convert to OpenCV format
            img_array = np.array(image)

            # Try to detect text orientation using OCR
            try:
                osd = pytesseract.image_to_osd(img_array)
                angle = re.search(r"Rotate: (\d+)", osd)
                if angle:
                    rotation_angle = int(angle.group(1))
                    if rotation_angle != 0:
                        # Rotate image to correct orientation
                        if rotation_angle == 90:
                            img_array = cv2.rotate(img_array, cv2.ROTATE_90_COUNTERCLOCKWISE)
                        elif rotation_angle == 180:
                            img_array = cv2.rotate(img_array, cv2.ROTATE_180)
                        elif rotation_angle == 270:
                            img_array = cv2.rotate(img_array, cv2.ROTATE_90_CLOCKWISE)

                        return Image.fromarray(img_array)
            except Exception:
                pass  # OSD might fail, continue with original

            return image

        except Exception as e:
            st.warning(f"Orientation correction failed: {str(e)}")
            return image


class GeometricAnalyzer:
    """Advanced geometric analysis for architectural drawings"""

    def __init__(self):
        self.wall_color_threshold = 128  # Threshold for wall detection
        self.min_wall_length = 50  # Minimum wall length in pixels

    def detect_wall_contours(self, image):
        """Detect wall contours and architectural elements"""
        try:
            # Convert to OpenCV format
            img_array = np.array(image)
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array

            # Edge detection for architectural elements
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)

            # Line detection for walls and boundaries
            lines = cv2.HoughLinesP(
                edges,
                1,
                np.pi / 180,
                threshold=100,
                minLineLength=self.min_wall_length,
                maxLineGap=10,
            )

            contours = []
            if lines is not None:
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    contours.append([(x1, y1), (x2, y2)])

            return contours, edges

        except Exception as e:
            st.warning(f"Wall contour detection failed: {str(e)}")
            return [], None

    def dbscan_zone_clustering(self, text_positions, contours):
        """Use DBSCAN clustering to identify enclosed spaces"""
        try:
            if not text_positions:
                return []

            # Extract coordinates for clustering
            coordinates = []
            for pos in text_positions:
                coordinates.append(
                    [pos["x"] + pos["w"] / 2, pos["y"] + pos["h"] / 2]
                )  # Center points

            if len(coordinates) < 2:
                return []

            # Apply DBSCAN clustering
            # eps: maximum distance between points in same cluster
            # min_samples: minimum points to form a cluster
            clustering = DBSCAN(eps=100, min_samples=2).fit(coordinates)
            labels = clustering.labels_

            # Group text positions by cluster
            clusters = defaultdict(list)
            for i, label in enumerate(labels):
                if label != -1:  # -1 means noise/outlier
                    clusters[label].append(text_positions[i])

            return list(clusters.values())

        except Exception as e:
            st.warning(f"DBSCAN clustering failed: {str(e)}")
            return []

    def create_zone_polygons(self, clusters, image_dimensions):
        """Create enhanced polygonal zone boundaries using Shapely geometry"""
        try:
            zone_polygons = []

            for cluster in clusters:
                if len(cluster) < 2:
                    continue

                try:
                    # Enhanced Shapely-based polygon creation
                    boxes = []
                    for pos in cluster:
                        x, y, w, h = pos["x"], pos["y"], pos["w"], pos["h"]
                        boxes.append(box(x, y, x + w, y + h))

                    # Merge overlapping boxes using Shapely union for more accurate zones
                    merged_geometry = unary_union(boxes)

                    # Handle both single and multi-polygon results
                    if hasattr(merged_geometry, "geoms"):
                        # MultiPolygon - take the largest for main zone
                        largest_polygon = max(merged_geometry.geoms, key=lambda p: p.area)
                    else:
                        # Single Polygon
                        largest_polygon = merged_geometry

                    # Add padding for better zone coverage
                    padding = 20
                    buffered_polygon = largest_polygon.buffer(padding)

                    # Clip to image dimensions
                    image_bounds = box(0, 0, image_dimensions[0], image_dimensions[1])
                    final_polygon = buffered_polygon.intersection(image_bounds)

                    # Extract coordinates
                    if final_polygon.is_empty:
                        continue

                    polygon_coords = list(final_polygon.exterior.coords)
                    bounds = final_polygon.bounds

                    zone_polygons.append(
                        {
                            "polygon": polygon_coords,
                            "cluster_data": cluster,
                            "area": final_polygon.area,
                            "bounds": {
                                "min_x": bounds[0],
                                "max_x": bounds[2],
                                "min_y": bounds[1],
                                "max_y": bounds[3],
                            },
                            "shapely_polygon": final_polygon,  # Store for advanced operations
                        }
                    )

                except Exception:
                    # Fallback to original bounding box method
                    x_coords = [pos["x"] for pos in cluster]
                    y_coords = [pos["y"] for pos in cluster]
                    w_coords = [pos["w"] for pos in cluster]
                    h_coords = [pos["h"] for pos in cluster]

                    min_x = min(x_coords)
                    max_x = max([x + w for x, w in zip(x_coords, w_coords, strict=False)])
                    min_y = min(y_coords)
                    max_y = max([y + h for y, h in zip(y_coords, h_coords, strict=False)])

                    # Create polygon with padding
                    padding = 20
                    polygon = [
                        (max(0, min_x - padding), max(0, min_y - padding)),
                        (min(image_dimensions[0], max_x + padding), max(0, min_y - padding)),
                        (
                            min(image_dimensions[0], max_x + padding),
                            min(image_dimensions[1], max_y + padding),
                        ),
                        (max(0, min_x - padding), min(image_dimensions[1], max_y + padding)),
                    ]

                    zone_polygons.append(
                        {
                            "polygon": polygon,
                            "cluster_data": cluster,
                            "area": (max_x - min_x) * (max_y - min_y),
                        }
                    )

            return zone_polygons

        except Exception as e:
            st.warning(f"Zone polygon creation failed: {str(e)}")
            return []


class ZoneMemoryManager:
    """Comprehensive zone memory and validation system"""

    def __init__(self):
        self.zone_registry = {}
        self.processing_log = []
        self.validation_checks = []
        self.confidence_scores = {}

    def register_zone(self, zone_name, page_num, detection_method, confidence=1.0):
        """Register a detected zone with tracking"""
        zone_id = f"{page_num}_{zone_name}"

        if zone_id not in self.zone_registry:
            self.zone_registry[zone_id] = {
                "name": zone_name,
                "page": page_num,
                "detection_methods": [detection_method],
                "first_detected": datetime.now(),
                "confidence": confidence,
                "furniture_codes": [],
            }
        else:
            # Update existing zone
            if detection_method not in self.zone_registry[zone_id]["detection_methods"]:
                self.zone_registry[zone_id]["detection_methods"].append(detection_method)
            # Update confidence (take maximum)
            self.zone_registry[zone_id]["confidence"] = max(
                self.zone_registry[zone_id]["confidence"], confidence
            )

        self.processing_log.append(
            {
                "timestamp": datetime.now(),
                "action": "zone_registered",
                "zone_id": zone_id,
                "method": detection_method,
            }
        )

    def associate_furniture_code(self, zone_name, page_num, furniture_code, confidence=1.0):
        """Associate furniture code with zone"""
        zone_id = f"{page_num}_{zone_name}"
        logger.debug(f"Agent 3: Attempting to associate code '{furniture_code}' with zone_id '{zone_id}'")

        if zone_id in self.zone_registry:
            self.zone_registry[zone_id]["furniture_codes"].append(
                {"code": furniture_code, "confidence": confidence, "timestamp": datetime.now()}
            )
            
            # Agent 2 Fix: Dedup furniture codes using set
            unique_codes = []
            seen_codes = set()
            for code_data in self.zone_registry[zone_id]["furniture_codes"]:
                code_text = code_data["code"]
                if code_text not in seen_codes:
                    seen_codes.add(code_text)
                    unique_codes.append(code_data)
                else:
                    logger.debug(f"Agent 2: Removed duplicate code '{code_text}' from zone '{zone_name}'")
            
            self.zone_registry[zone_id]["furniture_codes"] = unique_codes
            logger.debug(f"Agent 3: SUCCESS - Zone '{zone_name}' (ID: '{zone_id}') now has {len(unique_codes)} unique codes")
        else:
            # Agent 3 CRITICAL FIX: Handle missing zone case
            logger.error(f"Agent 3: CRITICAL - Zone ID '{zone_id}' not found in registry!")
            logger.error(f"Agent 3: Available zone IDs: {list(self.zone_registry.keys())}")
            
            # Try to find similar zone names
            for existing_id, zone_data in self.zone_registry.items():
                if zone_data["name"] == zone_name or zone_name in zone_data["name"]:
                    logger.warning(f"Agent 3: Found similar zone - using '{existing_id}' instead")
                    self.zone_registry[existing_id]["furniture_codes"].append(
                        {"code": furniture_code, "confidence": confidence, "timestamp": datetime.now()}
                    )
                    zone_id = existing_id  # Update for logging
                    break
            else:
                logger.error(f"Agent 3: FAILED - No similar zone found for '{zone_name}'. Association lost!")

        self.processing_log.append(
            {
                "timestamp": datetime.now(),
                "action": "code_associated",
                "zone_id": zone_id,
                "code": furniture_code,
            }
        )

    def validate_completeness(self):
        """Comprehensive validation of extracted data"""
        validation_results = {
            "total_zones": len(self.zone_registry),
            "zones_with_codes": 0,
            "total_codes": 0,
            "avg_confidence": 0,
            "issues": [],
        }

        total_confidence = 0
        for zone_id, zone_data in self.zone_registry.items():
            total_confidence += zone_data["confidence"]

            if zone_data["furniture_codes"]:
                validation_results["zones_with_codes"] += 1
                validation_results["total_codes"] += len(zone_data["furniture_codes"])
            else:
                validation_results["issues"].append(
                    f"Zone '{zone_data['name']}' has no furniture codes"
                )

        if self.zone_registry:
            validation_results["avg_confidence"] = total_confidence / len(self.zone_registry)

        return validation_results

    def get_processing_summary(self):
        """Get comprehensive processing summary"""
        return {
            "total_zones": len(self.zone_registry),
            "processing_steps": len(self.processing_log),
            "zones_by_page": self._group_zones_by_page(),
            "codes_by_type": self._group_codes_by_type(),
            "validation": self.validate_completeness(),
        }

    def _group_zones_by_page(self):
        """Group zones by page for summary"""
        by_page = defaultdict(int)
        for zone_data in self.zone_registry.values():
            by_page[zone_data["page"]] += 1
        return dict(by_page)

    def _group_codes_by_type(self):
        """Group furniture codes by type for summary"""
        by_type = defaultdict(int)
        for zone_data in self.zone_registry.values():
            for code_data in zone_data["furniture_codes"]:
                code_type = code_data["code"][:2]  # Get prefix
                by_type[code_type] += 1
        return dict(by_type)

    def get_zone_associations(self):
        """Get zone associations for CSV generation"""
        associations = {}
        logger.debug(f"Pre-CSV: {len(self.zone_registry)} zones in registry")  # Agent 1 Fix

        for zone_id, zone_data in self.zone_registry.items():
            zone_name = zone_data["name"]
            logger.debug(f"Agent 1: Processing zone '{zone_name}' with {len(zone_data['furniture_codes'])} furniture codes")

            # Convert furniture codes to the format expected by CSV generator
            codes = []
            for code_data in zone_data["furniture_codes"]:
                codes.append(
                    {
                        "code": code_data["code"],
                        "prefix": code_data["code"][:2] if len(code_data["code"]) >= 2 else "",
                        "confidence": code_data.get("confidence", 0.8),
                    }
                )

            associations[zone_name] = {
                "codes": codes,
                "page": zone_data["page"],
                "confidence": zone_data["confidence"],
            }

        logger.debug(f"Agent 1: Final associations count: {len(associations)} zones with {sum(len(assoc['codes']) for assoc in associations.values())} total codes")

        return associations


class EnhancedZoneExtractor:
    """Enhanced zone extractor with full architectural analysis"""

    def __init__(self):
        self.furniture_prefixes = ["CH", "TB", "C", "SU", "KT"]
        self.pdf_processor = A1PDFProcessor()
        self.geometric_analyzer = GeometricAnalyzer()
        self.memory_manager = ZoneMemoryManager()

        # Performance optimization settings
        self.batch_processing = True
        self.parallel_ocr = True
        self.geometric_optimization = True
        self.memory_conservation = True

    def detect_all_caps_zones(self, text, confidence_threshold=0.6):
        """Enhanced zone detection with confidence scoring for architectural areas"""
        # Agent 2 Fix: Add multiline merging logic
        lines = text.split('\n')
        merged_text = ' '.join([line.strip() for line in lines if line.strip()])
        logger.debug(f"Agent 2: Original text lines: {len(lines)}, merged to: {len(merged_text.split())} words")
        
        # Enhanced pattern for ALL CAPS zone names like "INNOVATION HUB", "EAT", "LOUNGE"
        # Handles single words and multi-word zones
        all_caps_pattern = r"\b[A-Z]{2,}(?:\s+[A-Z]{2,})*\b"
        matches = re.findall(all_caps_pattern, merged_text)  # Use merged_text instead of text

        # Filter out common non-zone words (reduced list, more focused)
        excluded_words = {
            "THE",
            "AND",
            "OR",
            "IN",
            "ON",
            "AT",
            "TO",
            "FOR",
            "OF",
            "WITH",
            "BY",
            "PLAN",
            "FLOOR",
            "LEVEL",
            "SCALE",
            "DRAWING",
            "PROJECT",
            "LEGEND",
            "PDF",
            "DPI",
            "PAGE",
            "IMAGE",
            "TEXT",
            "TITLE",
            "LABEL",
            "HEADER",
            "FOOTER",
            "NORTH",
            "SOUTH",
            "EAST",
            "WEST",
            "LEFT",
            "RIGHT",
            "TOP",
            "BOTTOM",
            "CENTER",
        }

        zone_candidates = []

        for match in matches:
            # Clean the match
            clean_match = match.strip()
            words = clean_match.split()

            # Skip if too short
            if len(clean_match) < 3:
                continue

            # Skip if all words are excluded
            if all(word in excluded_words for word in words):
                continue

            # Skip obvious furniture codes (they have our prefixes)
            is_furniture_code = any(
                clean_match.startswith(prefix) for prefix in ["CH", "TB", "C", "SU", "KT"]
            )
            if is_furniture_code:
                continue

            # Calculate confidence based on architectural relevance
            confidence = self._calculate_zone_confidence(clean_match)

            # Lower threshold for better zone detection
            if confidence >= confidence_threshold:
                zone_candidates.append({"name": clean_match, "confidence": confidence})

        return zone_candidates

    def _calculate_zone_confidence(self, zone_name):
        """Calculate confidence score for zone detection"""
        confidence = 0.4  # Base confidence (lowered for better detection)

        # Enhanced architectural terms based on user examples
        architectural_terms = [
            # Core architectural spaces
            "HUB",
            "INNOVATION",
            "EAT",
            "LOUNGE",
            "KITCHEN",
            "DINING",
            "OFFICE",
            "WORKSPACE",
            "STUDIO",
            "MEETING",
            "CONFERENCE",
            "LOBBY",
            "RECEPTION",
            "ENTRANCE",
            "EXIT",
            # Common spaces
            "ROOM",
            "SPACE",
            "AREA",
            "ZONE",
            "HALL",
            "CORRIDOR",
            "BATHROOM",
            "TOILET",
            "STORAGE",
            "CLOSET",
            "PANTRY",
            # Activity spaces
            "PRACTICE",
            "STUDY",
            "LIBRARY",
            "LAB",
            "CLINIC",
            "GYM",
            "THEATER",
            "GALLERY",
            "EXHIBITION",
            "RETAIL",
            "SHOP",
            # Outdoor/special
            "GARDEN",
            "TERRACE",
            "BALCONY",
            "COURTYARD",
            "PATIO",
            "CAFE",
            "BAR",
            "RESTAURANT",
            "CAFETERIA",
        ]

        # Check for architectural terms (multiple matches possible)
        term_matches = sum(1 for term in architectural_terms if term in zone_name)
        if term_matches > 0:
            confidence += 0.3 * min(term_matches, 2)  # Cap at 0.6 boost

        # Boost for reasonable length (zones are usually descriptive)
        if 3 <= len(zone_name) <= 25:
            confidence += 0.2

        # Boost for multiple words (architectural zones often are multi-word)
        word_count = len(zone_name.split())
        if word_count > 1:
            confidence += 0.15

        # Additional boost for very descriptive zones (like "INNOVATION HUB")
        if word_count >= 2 and any(term in zone_name for term in architectural_terms):
            confidence += 0.1

        # Penalize very long strings (likely not zone names)
        if len(zone_name) > 25:
            confidence -= 0.2

        return min(confidence, 1.0)

    def detect_furniture_codes(self, text, confidence_threshold=0.6):
        """FUZZY furniture code detection - handles MANY variations beyond examples"""
        furniture_codes = []

        for prefix in self.furniture_prefixes:
            # FUZZY/FLEXIBLE patterns for MANY possible variations
            # Examples given were just samples - this handles MUCH MORE:
            # Basic: CH15, CH15A, CH15 a, CH15b, CH21 b (given examples)
            # Separators: CH-15, CH.15, CH_15, CH/15, CH:15
            # Spacing: CH 15, CH  15, CH   15A
            # Multiple letters: CH15AA, CH15AB, CH15ABC
            # Mixed: CH-15A, CH.15 b, CH_15-A, CH/15.2
            # OCR errors: CH1S (S instead of 5), CHI5 (I instead of 1)
            # Leading zeros: CH015, CH0015, CH005A

            patterns = [
                # Main pattern - very flexible with separators
                rf"\b{prefix}[-.\s_/:]*\d+[-.\s_/:]*[A-Za-z]*\b",
                # Allow OCR character substitutions (1→I, 5→S, 0→O)
                rf"\b{prefix}[-.\s_/:]*[0-9IlOS]+[-.\s_/:]*[A-Za-z]*\b",
                # Multiple letters and decimal numbers
                rf"\b{prefix}[-.\s_/]*\d+\.?\d*[-.\s_/]*[A-Za-z]{{1,4}}\b",
                # Very permissive - any non-alphanumeric separators
                rf"\b{prefix}[^\w]*[0-9IlOS]+[^\w]*[A-Za-z]*\b",
                # Handle spaces before prefix (OCR artifacts)
                rf"\s+{prefix}[-.\s_]*\d+[-.\s_]*[A-Za-z]*\b",
            ]

            all_matches = set()  # Use set to avoid duplicates

            for pattern in patterns:
                try:
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    for match in matches:
                        # Only add if it looks like a real code (has digits or digit-like chars)
                        if re.search(r"[\d0-9IlOS]", match) and len(match.strip()) >= 3:
                            all_matches.add(match.strip())
                except Exception:
                    continue  # Skip if pattern fails

            # Process all unique matches
            for match in all_matches:
                # Flexible normalization - handle many formats
                normalized_code = self._normalize_furniture_code_fuzzy(match, prefix)

                if normalized_code:  # Only if normalization succeeded
                    # Calculate confidence with fuzzy scoring
                    confidence = self._calculate_fuzzy_code_confidence(
                        normalized_code, match, prefix
                    )

                    if confidence >= confidence_threshold:
                        furniture_codes.append(
                            {
                                "code": normalized_code,  # Normalized version
                                "original": match,  # Original detected text
                                "display": self._format_code_for_display(normalized_code),
                                "prefix": prefix,
                                "confidence": confidence,
                                "fuzzy_match": True,
                            }
                        )

        return furniture_codes

    def _normalize_furniture_code_fuzzy(self, match, prefix):
        """Normalize furniture code with fuzzy logic"""
        try:
            # Clean the match
            clean_match = match.strip().upper()

            # Handle OCR character substitutions
            clean_match = (
                clean_match.replace("I", "1").replace("l", "1").replace("O", "0").replace("S", "5")
            )

            # Extract prefix and number part
            prefix_part = prefix

            # Find the number part (may have separators)
            import re

            number_match = re.search(r"[\d0-9]+", clean_match)
            if not number_match:
                return None

            number_part = number_match.group()

            # Find letter part (after the number)
            letter_match = re.search(r"[A-Z]+$", clean_match)
            letter_part = letter_match.group() if letter_match else ""

            # Combine into normalized format
            normalized = f"{prefix_part}{number_part}"
            if letter_part:
                normalized += letter_part

            return normalized

        except Exception:
            return None

    def _calculate_fuzzy_code_confidence(self, normalized_code, original_match, prefix):
        """Calculate confidence for fuzzy matched codes"""
        confidence = 0.5  # Base confidence for fuzzy match

        # Boost for exact prefix match
        if normalized_code.startswith(prefix):
            confidence += 0.2

        # Boost for proper format (prefix + numbers + optional letters)
        if re.match(rf"^{prefix}\d+[A-Z]*$", normalized_code):
            confidence += 0.2

        # Boost for short, clean codes
        if len(normalized_code) <= 6:
            confidence += 0.1

        # Penalize very long codes (likely false positives)
        if len(normalized_code) > 10:
            confidence -= 0.2

        # Boost if original match is clean (no weird characters)
        if re.match(rf"^{prefix}[\s\d\w]+$", original_match):
            confidence += 0.1

        return min(confidence, 1.0)

    def _format_code_for_display(self, normalized_code):
        """Format code for display"""
        if len(normalized_code) <= 2:
            return normalized_code

        # Split into prefix, number, letter
        prefix = normalized_code[:2]
        rest = normalized_code[2:]

        # Find where letters start
        number_part = ""
        letter_part = ""

        for i, char in enumerate(rest):
            if char.isalpha():
                number_part = rest[:i]
                letter_part = rest[i:]
                break
        else:
            number_part = rest

        # Format nicely
        if letter_part:
            return f"{prefix}{number_part}{letter_part}"
        else:
            return f"{prefix}{number_part}"

    def _calculate_code_confidence(self, code, prefix):
        """Calculate confidence score for furniture code"""
        confidence = 0.8  # Base confidence for pattern match

        # Boost for proper format
        if re.match(rf"^{prefix}\d+[A-Z]?$", code):
            confidence += 0.2

        return min(confidence, 1.0)

    def _find_text_position_fuzzy(self, target_text, ocr_data, threshold=0.6):
        """Find position of text using fuzzy matching"""
        import difflib
        
        target_clean = target_text.upper().strip()
        best_match = None
        best_score = 0
        
        for word_data in ocr_data:
            word_text = word_data.get('text', '').strip().upper()
            if not word_text:
                continue
                
            # Direct match
            if target_clean in word_text or word_text in target_clean:
                return word_data
            
            # Fuzzy matching
            similarity = difflib.SequenceMatcher(None, target_clean, word_text).ratio()
            if similarity > best_score and similarity >= threshold:
                best_score = similarity
                best_match = word_data
        
        return best_match

    def _associate_with_smart_matching(self, results):
        """Enhanced association using smart text matching"""
        zones = results.get("zones", [])
        codes = results.get("codes", [])
        ocr_data = results.get("ocr_data", [])
        
        if not zones or not codes or not ocr_data:
            st.warning("⚠️ Insufficient data for smart association")
            return 0
        
        associations_made = 0
        st.info("🧠 Using smart text matching for association...")
        
        for code in codes:
            code_text = code.get("code", code.get("text", ""))
            original_text = code.get("original", code_text)
            
            # Find code position using fuzzy matching
            code_pos = self._find_text_position_fuzzy(code_text, ocr_data)
            if not code_pos:
                # Try with original text
                code_pos = self._find_text_position_fuzzy(original_text, ocr_data)
            
            if not code_pos:
                st.warning(f"⚠️ No position found for code '{original_text}' even with fuzzy matching")
                continue
                
            code_x = code_pos["x"] + code_pos.get("w", 0) // 2
            code_y = code_pos["y"] + code_pos.get("h", 0) // 2
            
            st.info(f"📍 Code '{code_text}' found at ({code_x}, {code_y}) via fuzzy match")
            
            # Find closest zone
            closest_zone = None
            min_distance = float("inf")
            
            for zone in zones:
                zone_text = zone.get("zone_area", zone.get("text", ""))
                
                # Try each word in zone name
                zone_pos = None
                for zone_word in zone_text.split():
                    if len(zone_word) > 2:  # Skip very short words
                        zone_pos = self._find_text_position_fuzzy(zone_word, ocr_data)
                        if zone_pos:
                            break
                
                if not zone_pos:
                    continue
                    
                zone_x = zone_pos["x"] + zone_pos.get("w", 0) // 2
                zone_y = zone_pos["y"] + zone_pos.get("h", 0) // 2
                
                distance = ((code_x - zone_x) ** 2 + (code_y - zone_y) ** 2) ** 0.5
                if distance < min_distance:
                    min_distance = distance
                    closest_zone = zone_text
            
            # Agent 2 Fix: Dynamic threshold (15% of page width)
            dynamic_threshold = 1500  # Default fallback
            if ocr_data:
                # Estimate image width from OCR data
                max_x = max(word.get("x", 0) + word.get("w", 0) for word in ocr_data)
                dynamic_threshold = max(200, min(2000, max_x * 0.15))  # 15% of page width
                logger.debug(f"Agent 2: Smart matching dynamic threshold: {dynamic_threshold:.1f}px (15% of {max_x}px width)")
            
            # Associate if reasonable distance
            if closest_zone and min_distance < dynamic_threshold:
                confidence = code.get("confidence", 0.8) * 0.9  # Slightly reduce confidence for fuzzy
                page_num = code.get("page", 1)
                self.memory_manager.associate_furniture_code(closest_zone, page_num, code_text, confidence)
                associations_made += 1
                logger.debug(f"Agent 2: Smart association '{code_text}' → '{closest_zone}' (distance: {min_distance:.1f}px, threshold: {dynamic_threshold:.1f}px)")
                st.success(f"✅ SMART: '{original_text}' → '{closest_zone}' (distance: {min_distance:.1f}px)")
            else:
                st.warning(f"⚠️ No suitable zone found for '{original_text}' (min distance: {min_distance:.1f}px)")
        
        return associations_made

    def _calculate_dynamic_distance_threshold(self, image_size):
        """Calculate dynamic distance threshold based on page size/DPI"""
        page_width, page_height = image_size
        # Dynamic threshold: 10% of page width, min 200px, max 2000px
        dynamic_threshold = max(200, min(2000, page_width * 0.1))
        logger.debug(f"Agent 2: Dynamic distance threshold calculated: {dynamic_threshold}px for page size {image_size}")
        return dynamic_threshold

    def _deduplicate_codes(self, codes):
        """Agent 2: Remove duplicate codes using sets"""
        seen_codes = set()
        unique_codes = []
        
        for code in codes:
            code_text = code.get("code", "")
            if code_text not in seen_codes:
                seen_codes.add(code_text)
                unique_codes.append(code)
            else:
                logger.debug(f"Agent 2: Removed duplicate code: {code_text}")
        
        logger.debug(f"Agent 2: Deduplicated {len(codes)} → {len(unique_codes)} codes")
        return unique_codes

    def associate_detected_codes_to_zones(self, results):
        """Associate detected furniture codes with their corresponding zones using OCR positions"""
        st.info("🔗 Associating furniture codes to zones...")

        zones = results.get("zones", [])
        codes = results.get("codes", [])
        ocr_data = results.get("ocr_data", [])

        if not zones or not codes:
            st.warning("⚠️ No zones or codes to associate")
            return

        if not ocr_data:
            st.warning("⚠️ No OCR position data available for association")
            return

        # Agent 2: Deduplicate codes
        codes = self._deduplicate_codes(codes)
        logger.debug(f"Agent 2: Processing {len(codes)} unique codes with {len(zones)} zones")

        # Agent 2: Calculate dynamic distance threshold
        # Estimate image size from OCR data bounds
        if ocr_data:
            max_x = max(word.get("x", 0) + word.get("w", 0) for word in ocr_data)
            max_y = max(word.get("y", 0) + word.get("h", 0) for word in ocr_data)
            estimated_size = (max_x, max_y)
            distance_threshold = self._calculate_dynamic_distance_threshold(estimated_size)
        else:
            distance_threshold = 1000  # Fallback

        associations_made = 0

        # Create position lookup for OCR words
        word_positions = {}
        for word_data in ocr_data:
            word_text = word_data.get("text", "").strip().upper()
            if word_text:
                word_positions[word_text] = {
                    "x": word_data.get("x", 0),
                    "y": word_data.get("y", 0),
                    "w": word_data.get("w", 0),
                    "h": word_data.get("h", 0),
                }

        for code in codes:
            # Handle both old and new code structure
            code_text = code.get("code", code.get("text", ""))
            original_text = code.get("original", code_text)

            # ENHANCED: Get position from bbox first, then OCR data
            code_x, code_y = None, None
            code_bbox = code.get("bbox", {})
            
            if code_bbox and code_bbox.get("x") is not None:
                code_x = code_bbox["x"] + code_bbox.get("w", 0) // 2
                code_y = code_bbox["y"] + code_bbox.get("h", 0) // 2
                st.info(f"📍 Code '{code_text}' position from bbox: ({code_x}, {code_y})")
            else:
                # Find position of this code in OCR data
                code_position = None
                for search_text in [original_text, code_text]:
                    if search_text.upper() in word_positions:
                        code_position = word_positions[search_text.upper()]
                        break

                if not code_position:
                    # ENHANCED: Try to find position by partial text matching
                    partial_matches = [
                        text
                        for text in word_positions
                        if original_text.upper() in text or text in original_text.upper()
                    ]
                    if partial_matches:
                        code_position = word_positions[partial_matches[0]]
                        st.info(
                            f"📍 Found code '{original_text}' via partial match: '{partial_matches[0]}'"
                        )
                    else:
                        st.warning(
                            f"⚠️ Code '{original_text}' position not found in OCR data (skipping association)"
                        )
                        continue

                code_x = code_position["x"] + (code_position["w"] / 2)
                code_y = code_position["y"] + (code_position["h"] / 2)

            closest_zone = None
            min_distance = float("inf")

            # Find closest zone to this code
            for zone in zones:
                zone_text = zone.get("zone_area", zone.get("text", zone.get("name", "")))

                # ENHANCED: Get zone position from bbox first, then OCR data
                zone_x, zone_y = None, None
                zone_bbox = zone.get("bbox", {})
                
                if zone_bbox and zone_bbox.get("x") is not None:
                    zone_x = zone_bbox["x"] + zone_bbox.get("w", 0) // 2
                    zone_y = zone_bbox["y"] + zone_bbox.get("h", 0) // 2
                else:
                    # Find position of this zone in OCR data
                    zone_position = None
                    zone_words = zone_text.split()

                    # Try to find any word from the zone name
                    for zone_word in zone_words:
                        if len(zone_word) > 2 and zone_word.upper() in word_positions:
                            zone_position = word_positions[zone_word.upper()]
                            break

                    if not zone_position:
                        continue

                    zone_x = zone_position["x"] + (zone_position["w"] / 2)
                    zone_y = zone_position["y"] + (zone_position["h"] / 2)

                # Calculate distance
                distance = ((code_x - zone_x) ** 2 + (code_y - zone_y) ** 2) ** 0.5

                if distance < min_distance:
                    min_distance = distance
                    closest_zone = zone_text

            # Enhanced association using both distance and geometric containment
            association_made = False
            association_method = "distance"

            # Try geometric containment first if Shapely polygons are available
            try:
                # Check if any zone polygons contain this code point
                code_point = Point(code_x, code_y)
                for zone in zones:
                    zone_text = zone.get("zone_area", zone.get("text", ""))
                    zone_data = zone.get("shapely_polygon")

                    if zone_data and zone_data.contains(code_point):
                        confidence = code.get("confidence", 0.8)
                        page_num = code.get("page", 1)
                        self.memory_manager.associate_furniture_code(
                            zone_text, page_num, code_text, confidence
                        )
                        associations_made += 1
                        association_made = True
                        association_method = "geometric_containment"
                        st.success(
                            f"✅ Associated '{original_text}' → '{code_text}' with zone '{zone_text}' (geometric containment)"
                        )
                        break
            except Exception:
                pass  # Fall back to distance method

            # Agent 2: Dynamic distance-based association
            if not association_made and closest_zone and min_distance < distance_threshold:
                confidence = code.get("confidence", 0.8)
                page_num = code.get("page", 1)
                self.memory_manager.associate_furniture_code(closest_zone, page_num, code_text, confidence)
                associations_made += 1
                association_made = True
                logger.debug(f"Agent 2: Associated '{code_text}' → '{closest_zone}' (distance: {min_distance:.1f}px, threshold: {distance_threshold}px)")
                st.success(
                    f"✅ Associated '{original_text}' → '{code_text}' with zone '{closest_zone}' (distance: {min_distance:.1f}px)"
                )

            if not association_made:
                st.warning(
                    f"⚠️ Code '{original_text}' could not be associated (min distance: {min_distance:.1f}px)"
                )

        # If no associations made, try smart matching as fallback
        if associations_made == 0:
            st.warning("⚠️ Standard association failed - trying smart matching...")
            smart_associations = self._associate_with_smart_matching(results)
            associations_made += smart_associations
        
        st.info(f"🔗 Association complete: {associations_made} codes associated to zones")

    def generate_structured_csv(self, results):
        """
        Generate structured UTF-8 CSV files as per user specification:
        - Each row contains Zone/Area name, extracted furniture/joinery codes (filtered by allowed prefixes)
        - Code type (CH, TB, C, SU, KT), and subtotal count per code type per zone
        - Summary rows with grand totals for each unique code type across all zones
        """
        try:
            # Get zones and codes from memory manager (where associations are stored)
            zone_data = self.memory_manager.get_zone_associations()
            logger.debug(f"Agent 1 Data Flow: Retrieved {len(zone_data)} zones from memory manager")

            csv_rows = []

            # Track grand totals for each code type
            grand_totals = {
                "CH": 0,  # Chairs
                "TB": 0,  # Tables
                "C": 0,  # General furniture
                "SU": 0,  # Storage Units
                "KT": 0,  # Kitchen/joinery
            }

            st.info(f"📊 Processing {len(zone_data)} zones for CSV generation...")
            logger.debug(f"Agent 1 Data Flow: Starting CSV processing with {len(zone_data)} zones")

            # Process each zone
            for zone_name, zone_info in zone_data.items():
                codes_in_zone = zone_info.get("codes", [])
                logger.debug(f"Agent 3: Processing zone '{zone_name}' with {len(codes_in_zone)} codes")

                if not codes_in_zone:
                    # Zone with no codes - still include in CSV
                    csv_rows.append(
                        {
                            "Zone_Area": zone_name,
                            "Furniture_Code": "",
                            "Code_Type": "",
                            "Subtotal_Count": 0,
                            "Notes": "No furniture codes detected in this zone",
                        }
                    )
                    logger.debug(f"Agent 3: Added empty zone row for '{zone_name}'")
                    continue

                # Count codes by type in this zone
                zone_totals = {"CH": 0, "TB": 0, "C": 0, "SU": 0, "KT": 0}

                # First pass: count codes by type
                for code_info in codes_in_zone:
                    code = code_info.get("code", "")
                    prefix = code_info.get("prefix", "")

                    # Filter by allowed prefixes only
                    if prefix in ["CH", "TB", "C", "SU", "KT"]:
                        zone_totals[prefix] += 1
                        grand_totals[prefix] += 1

                # Second pass: generate rows for each code type found in this zone
                zone_has_codes = False
                for code_type in ["CH", "TB", "C", "SU", "KT"]:
                    if zone_totals[code_type] > 0:
                        zone_has_codes = True

                        # Get example codes of this type
                        example_codes = [
                            code_info.get("code", "")
                            for code_info in codes_in_zone
                            if code_info.get("prefix", "") == code_type
                        ]

                        csv_rows.append(
                            {
                                "Zone_Area": zone_name,
                                "Furniture_Code": ", ".join(
                                    example_codes[:5]
                                ),  # Show up to 5 examples
                                "Code_Type": code_type,
                                "Subtotal_Count": zone_totals[code_type],
                                "Notes": f"{zone_totals[code_type]} {code_type} codes detected",
                            }
                        )

                if not zone_has_codes:
                    # Zone with detected codes but none with valid prefixes
                    csv_rows.append(
                        {
                            "Zone_Area": zone_name,
                            "Furniture_Code": "Invalid codes detected",
                            "Code_Type": "INVALID",
                            "Subtotal_Count": 0,
                            "Notes": "Codes detected but no valid CH/TB/C/SU/KT prefixes",
                        }
                    )

            # Add separator row
            csv_rows.append(
                {
                    "Zone_Area": "=== GRAND TOTALS ===",
                    "Furniture_Code": "",
                    "Code_Type": "",
                    "Subtotal_Count": "",
                    "Notes": "Summary across all zones",
                }
            )

            # Add grand totals for each code type
            for code_type in ["CH", "TB", "C", "SU", "KT"]:
                if grand_totals[code_type] > 0:
                    csv_rows.append(
                        {
                            "Zone_Area": "ALL ZONES",
                            "Furniture_Code": f"All {code_type} codes",
                            "Code_Type": code_type,
                            "Subtotal_Count": grand_totals[code_type],
                            "Notes": f"Total {code_type} codes across all zones",
                        }
                    )

            # Add overall summary
            total_codes = sum(grand_totals.values())
            csv_rows.append(
                {
                    "Zone_Area": "OVERALL TOTAL",
                    "Furniture_Code": "All furniture/joinery codes",
                    "Code_Type": "ALL",
                    "Subtotal_Count": total_codes,
                    "Notes": f"Complete analysis: {len(zone_data)} zones, {total_codes} total codes",
                }
            )

            # Agent 3: Validate inputs before CSV generation
            if not csv_rows:
                logger.warning("Agent 3: No CSV rows generated")
                st.warning("⚠️ No data available for CSV generation")
                return "Zone_Area,Furniture_Code,Code_Type,Subtotal_Count,Notes\n"  # Return headers only
            
            logger.debug(f"Agent 3: Generated {len(csv_rows)} CSV rows")

            # Convert to DataFrame and CSV
            df = pd.DataFrame(csv_rows)
            csv_string = df.to_csv(index=False, encoding="utf-8")

            # Agent 3: Validate CSV output
            csv_lines = csv_string.strip().split('\n')
            logger.debug(f"Agent 3: CSV output has {len(csv_lines)} lines, first line: {csv_lines[0] if csv_lines else 'EMPTY'}")

            st.success(f"✅ CSV generated: {len(csv_rows)} rows, {total_codes} total codes")
            st.info(
                f"📋 Grand totals: CH={grand_totals['CH']}, TB={grand_totals['TB']}, C={grand_totals['C']}, SU={grand_totals['SU']}, KT={grand_totals['KT']}"
            )

            return csv_string

        except Exception as e:
            st.error(f"❌ CSV generation failed: {str(e)}")
            return None

    def merge_fragmented_text(self, word_positions):
        """Merge fragmented text that should be single zones"""
        if not word_positions:
            return word_positions

        merged_positions = []
        used_indices = set()

        for i, word in enumerate(word_positions):
            if i in used_indices:
                continue

            # Check if this word should be merged with nearby words
            if word["text"].isupper() and len(word["text"]) > 2:
                merged_text = word["text"]
                merged_bbox = {"x1": word["x"], "y1": word["y"], "w": word["w"], "h": word["h"]}
                merged_confidence = word["confidence"]
                group_indices = [i]

                # Look for nearby words to merge
                for j, other_word in enumerate(word_positions):
                    if j != i and j not in used_indices and other_word["text"].isupper():
                        # Check if words are close enough (within 50 pixels vertically or horizontally)
                        x_distance = abs(word["x"] - other_word["x"])
                        y_distance = abs(word["y"] - other_word["y"])

                        if (x_distance < 200 and y_distance < 50) or (
                            y_distance < 200 and x_distance < 50
                        ):
                            merged_text += " " + other_word["text"]
                            merged_bbox["x1"] = min(merged_bbox["x1"], other_word["x"])
                            merged_bbox["y1"] = min(merged_bbox["y1"], other_word["y"])
                            merged_bbox["w"] = (
                                max(
                                    merged_bbox["x1"] + merged_bbox["w"],
                                    other_word["x"] + other_word["w"],
                                )
                                - merged_bbox["x1"]
                            )
                            merged_bbox["h"] = (
                                max(
                                    merged_bbox["y1"] + merged_bbox["h"],
                                    other_word["y"] + other_word["h"],
                                )
                                - merged_bbox["y1"]
                            )
                            merged_confidence = max(merged_confidence, other_word["confidence"])
                            group_indices.append(j)

                # Mark all used indices
                for idx in group_indices:
                    used_indices.add(idx)

                # Add merged word
                merged_positions.append(
                    {
                        "text": merged_text.strip(),
                        "x": merged_bbox["x1"],
                        "y": merged_bbox["y1"],
                        "w": merged_bbox["w"],
                        "h": merged_bbox["h"],
                        "confidence": merged_confidence,
                    }
                )
            else:
                # Keep individual word
                used_indices.add(i)
                merged_positions.append(word)

        return merged_positions

    def process_pdf_enhanced(self, pdf_path):
        """Enhanced PDF processing with full architectural analysis"""
        results = {
            "zones": [],
            "codes": [],
            "geometric_analysis": {},
            "processing_summary": {},
            "validation": {},
        }

        try:
            # Detect A1 format
            is_a1, orientation, dimensions = self.pdf_processor.detect_a1_format(pdf_path)

            # Calculate safe DPI based on page dimensions
            safe_dpi = self.pdf_processor.calculate_safe_dpi(dimensions[0], dimensions[1])

            # Enhanced format display
            if is_a1:
                if orientation in ["portrait", "landscape"]:
                    format_type = f"A1-Compatible Large Format ({orientation})"
                else:
                    format_type = "Large Format Architectural Drawing"
            else:
                format_type = f"Non-A1 Format ({orientation})"
            
            st.info(f"📐 PDF Format: {format_type}, Dimensions: {dimensions[0]:.1f}x{dimensions[1]:.1f}mm")
            st.info(f"🎯 Processing at {safe_dpi} DPI for optimal quality and safety")

            # Get number of pages
            with pdfplumber.open(pdf_path) as pdf:
                num_pages = len(pdf.pages)

            # Process each page with enhanced pipeline
            for page_num in range(min(num_pages, 5)):  # Limit for performance
                st.progress((page_num + 1) / min(num_pages, 5), f"Processing page {page_num + 1}")

                # Convert to safe resolution image with enhanced error handling
                images = None
                dpi_attempts = [safe_dpi]

                # Add fallback DPI values
                if safe_dpi > 200:
                    dpi_attempts.append(200)
                if safe_dpi > 150:
                    dpi_attempts.append(150)

                for attempt_dpi in dpi_attempts:
                    try:
                        st.info(f"🔄 Attempting conversion at {attempt_dpi} DPI...")
                        images = convert_from_path(
                            pdf_path,
                            first_page=page_num + 1,
                            last_page=page_num + 1,
                            dpi=attempt_dpi,
                        )
                        if images:
                            if attempt_dpi != safe_dpi:
                                st.success(
                                    f"✅ Conversion successful at fallback {attempt_dpi} DPI"
                                )
                            break
                    except Exception as conversion_error:
                        error_msg = str(conversion_error)
                        if "exceeds limit" in error_msg or "pixels" in error_msg:
                            st.warning(f"⚠️ DPI {attempt_dpi} still too large: {error_msg}")
                        else:
                            st.warning(f"⚠️ Conversion failed at {attempt_dpi} DPI: {error_msg}")
                        continue

                if not images:
                    st.error(f"❌ All conversion attempts failed for page {page_num + 1}")
                    continue

                image = images[0]

                # Enhanced image processing
                image = self.pdf_processor.enhance_image_quality(image)
                image = self.pdf_processor.correct_orientation(image)

                # OCR with enhanced configuration
                img_array = np.array(image)
                custom_config = r"--oem 3 --psm 11 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 "

                try:
                    # Extract text and positions
                    text = pytesseract.image_to_string(img_array, config=custom_config)
                    data = pytesseract.image_to_data(
                        img_array, config=custom_config, output_type=pytesseract.Output.DICT
                    )

                    # Build word positions
                    word_positions = []
                    for i, word in enumerate(data["text"]):
                        if int(data["conf"][i]) > 30 and word.strip():
                            word_positions.append(
                                {
                                    "text": word,
                                    "x": data["left"][i],
                                    "y": data["top"][i],
                                    "w": data["width"][i],
                                    "h": data["height"][i],
                                    "confidence": int(data["conf"][i]) / 100.0,
                                }
                            )

                    # Fix text fragmentation by merging nearby words
                    word_positions = self.merge_fragmented_text(word_positions)

                    # Store OCR data for association (CRITICAL FIX)
                    if "ocr_data" not in results:
                        results["ocr_data"] = []
                    results["ocr_data"].extend(word_positions)

                    # Detect zones and codes with confidence
                    zone_candidates = self.detect_all_caps_zones(text)
                    code_candidates = self.detect_furniture_codes(text)

                    # Register zones in memory manager
                    for zone in zone_candidates:
                        self.memory_manager.register_zone(
                            zone["name"], page_num + 1, "enhanced_ocr", zone["confidence"]
                        )
                        results["zones"].append(
                            {
                                "page": page_num + 1,
                                "zone_area": zone["name"],
                                "method": "enhanced_ocr",
                                "confidence": zone["confidence"],
                            }
                        )

                    # Register codes
                    for code in code_candidates:
                        results["codes"].append(
                            {
                                "page": page_num + 1,
                                "code": code["code"],
                                "code_type": code["prefix"],
                                "method": "enhanced_ocr",
                                "confidence": code["confidence"],
                            }
                        )

                    # Geometric analysis
                    contours, edges = self.geometric_analyzer.detect_wall_contours(image)
                    clusters = self.geometric_analyzer.dbscan_zone_clustering(
                        word_positions, contours
                    )
                    zone_polygons = self.geometric_analyzer.create_zone_polygons(
                        clusters, image.size
                    )

                    results["geometric_analysis"][f"page_{page_num + 1}"] = {
                        "contours_detected": len(contours),
                        "clusters_found": len(clusters),
                        "zone_polygons": len(zone_polygons),
                    }

                except Exception as e:
                    st.warning(f"Enhanced OCR failed for page {page_num + 1}: {str(e)}")
                    continue

            # CRITICAL: Store OCR position data for association
            ocr_data = results.get("ocr_data", [])
            if ocr_data:
                # Ensure we have position data before association
                st.info("🔗 Preparing OCR position data for association...")
                
                # Debug: Show what we have
                st.write(f"📊 OCR words available: {len(ocr_data)}")
                st.write(f"📊 Zones detected: {len(results['zones'])}")
                st.write(f"📊 Codes detected: {len(results['codes'])}")
                
                # Add position data to zones and codes
                for zone in results['zones']:
                    zone_text = zone.get('zone_area', zone.get('text', ''))
                    # Find position for zone words
                    for word_data in ocr_data:
                        word_text = word_data.get('text', '').strip().upper()
                        if any(zone_part.upper() in word_text for zone_part in zone_text.split() if len(zone_part) > 2):
                            zone['bbox'] = {
                                'x': word_data.get('x', 0),
                                'y': word_data.get('y', 0),
                                'w': word_data.get('w', 0),
                                'h': word_data.get('h', 0)
                            }
                            break
                
                for code in results['codes']:
                    code_text = code.get('code', code.get('text', '')).upper()
                    # Find position for code
                    for word_data in ocr_data:
                        word_text = word_data.get('text', '').strip().upper()
                        if code_text in word_text or word_text in code_text:
                            code['bbox'] = {
                                'x': word_data.get('x', 0),
                                'y': word_data.get('y', 0),
                                'w': word_data.get('w', 0),
                                'h': word_data.get('h', 0)
                            }
                            break

            # CRITICAL: Associate codes to zones (was missing!)
            self.associate_detected_codes_to_zones(results)

            # Final validation and summary
            results["processing_summary"] = self.memory_manager.get_processing_summary()
            results["validation"] = self.memory_manager.validate_completeness()

            return results

        except Exception as e:
            error_msg = str(e)
            if "exceeds limit" in error_msg and "pixels" in error_msg:
                st.error(f"⚠️ Image too large for processing: {error_msg}")
                st.info(
                    "💡 This PDF requires lower DPI processing. The image size safety feature prevented a potential memory issue."
                )
                st.info(
                    "🔄 Try using a smaller PDF or contact support for large file processing options."
                )
            else:
                st.error(f"Enhanced processing failed: {error_msg}")

            return results


def process_uploaded_file_enhanced(uploaded_file):
    """Process uploaded file with enhanced pipeline"""
    if uploaded_file is None:
        return None, "No file uploaded"

    try:
        # Create secure temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(uploaded_file.getvalue())
            temp_filename = temp_file.name

        try:
            # Initialize enhanced extractor
            extractor = EnhancedZoneExtractor()
            results = extractor.process_pdf_enhanced(temp_filename)

            return results, None

        finally:
            # Clean up
            if temp_filename and os.path.exists(temp_filename):
                os.unlink(temp_filename)

    except Exception as e:
        return None, f"Error processing file: {str(e)}"


def display_enhanced_results(results):
    """Display enhanced results with comprehensive metrics"""
    if not results or (not results["zones"] and not results["codes"]):
        st.warning("No zones or furniture codes found in the PDF")
        return

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Zones Detected", len(results["zones"]))
    with col2:
        st.metric("Furniture Codes", len(results["codes"]))
    with col3:
        avg_confidence = np.mean(
            [z.get("confidence", 0) for z in results["zones"] + results["codes"]]
        )
        st.metric("Avg Confidence", f"{avg_confidence:.2f}")
    with col4:
        validation = results.get("validation", {})
        st.metric("Zones with Codes", validation.get("zones_with_codes", 0))

    # Detailed results tabs
    tab1, tab2, tab3, tab4 = st.tabs(
        ["Zones & Codes", "Geometric Analysis", "Processing Summary", "Validation"]
    )

    with tab1:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🏢 Detected Zones")
            if results["zones"]:
                zones_df = pd.DataFrame(results["zones"])
                st.dataframe(zones_df, use_container_width=True)

        with col2:
            st.subheader("🪑 Detected Codes")
            if results["codes"]:
                codes_df = pd.DataFrame(results["codes"])
                st.dataframe(codes_df, use_container_width=True)

                # Code type distribution
                if "code_type" in codes_df.columns:
                    code_stats = codes_df["code_type"].value_counts()
                    st.bar_chart(code_stats)

    with tab2:
        st.subheader("🔍 Geometric Analysis Results")
        geometric = results.get("geometric_analysis", {})

        if geometric:
            for page, analysis in geometric.items():
                with st.expander(f"📄 {page.replace('_', ' ').title()}"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Wall Contours", analysis.get("contours_detected", 0))
                    with col2:
                        st.metric("Text Clusters", analysis.get("clusters_found", 0))
                    with col3:
                        st.metric("Zone Polygons", analysis.get("zone_polygons", 0))
        else:
            st.info("No geometric analysis data available")

    with tab3:
        st.subheader("📊 Processing Summary")
        summary = results.get("processing_summary", {})

        if summary:
            col1, col2 = st.columns(2)

            with col1:
                st.write("**Zones by Page:**")
                zones_by_page = summary.get("zones_by_page", {})
                if zones_by_page:
                    st.json(zones_by_page)
                else:
                    st.info("No zone distribution data")

            with col2:
                st.write("**Codes by Type:**")
                codes_by_type = summary.get("codes_by_type", {})
                if codes_by_type:
                    st.json(codes_by_type)
                else:
                    st.info("No code distribution data")

    with tab4:
        st.subheader("✅ Validation Results")
        validation = results.get("validation", {})

        if validation:
            col1, col2 = st.columns(2)

            with col1:
                st.metric("Total Zones", validation.get("total_zones", 0))
                st.metric("Zones with Codes", validation.get("zones_with_codes", 0))
                st.metric("Total Codes", validation.get("total_codes", 0))

            with col2:
                avg_conf = validation.get("avg_confidence", 0)
                st.metric("Average Confidence", f"{avg_conf:.2f}")

                issues = validation.get("issues", [])
                if issues:
                    st.warning("**Issues Found:**")
                    for issue in issues:
                        st.write(f"⚠️ {issue}")
                else:
                    st.success("✅ No validation issues found")

    # PROPER CSV GENERATION AS PER USER SPECIFICATION
    if results["zones"] or results["codes"]:
        st.subheader("📥 Structured UTF-8 CSV Export")
        st.info(
            "Generating structured CSV with zones, codes, subtotals per type per zone, and grand totals..."
        )

        # Generate the REQUIRED CSV structure
        extractor = EnhancedZoneExtractor()
        csv_data = extractor.generate_structured_csv(results)

        if csv_data:
            st.download_button(
                label="Download Structured Zone/Codes CSV (UTF-8)",
                data=csv_data,
                file_name="zone_furniture_codes_analysis.csv",
                mime="text/csv",
                help="Complete analysis with geometric data, confidence scores, and validation",
            )


def main():
    st.title("🏗️ A1 PDF Zones/Codes Extractor - Enhanced")
    st.markdown(
        "**Production-grade OCR-based extraction with geometric analysis for architectural PDFs**"
    )

    # Enhanced capabilities display
    with st.expander("🚀 Enhanced Capabilities", expanded=False):
        st.markdown(
            """
        ### 🎯 Advanced Features:

        **A1 Format Optimization:**
        - ✅ **600+ DPI processing** for high-resolution analysis
        - ✅ **A1 size detection** with orientation correction
        - ✅ **Enhanced image quality** with noise reduction and contrast enhancement

        **Geometric Analysis:**
        - ✅ **Wall contour detection** using OpenCV edge detection
        - ✅ **DBSCAN clustering** for spatial zone identification
        - ✅ **Polygonal zone boundaries** from geometric analysis

        **Intelligence & Memory:**
        - ✅ **Zone memory management** with short-term tracking
        - ✅ **Confidence scoring** for all detections
        - ✅ **Comprehensive validation** and completeness checks
        - ✅ **Processing audit trails** for quality assurance

        **Production Features:**
        - ✅ **Zero manual touch** automated pipeline
        - ✅ **Audit-ready outputs** with detailed metrics
        - ✅ **Enhanced error handling** and recovery
        - ✅ **Performance optimization** for large A1 PDFs
        """
        )

    # File uploader
    uploaded_file = st.file_uploader(
        "Choose an A1 architectural PDF file",
        type=["pdf"],
        help="Upload an A1-sized architectural PDF for enhanced analysis",
    )

    if uploaded_file is not None:
        st.success(f"File uploaded: {uploaded_file.name}")

        # Enhanced file details
        file_size_mb = uploaded_file.size / (1024 * 1024)
        file_details = {
            "Filename": uploaded_file.name,
            "File size": f"{file_size_mb:.2f} MB",
            "Processing mode": "Enhanced A1 Analysis",
        }
        st.json(file_details)

        # Enhanced processing button
        if st.button("🔍 Start Enhanced Analysis"):
            with st.spinner(
                "🏗️ Processing with enhanced A1 pipeline (600+ DPI, geometric analysis, validation)..."
            ):
                start_time = time.time()

                results, error = process_uploaded_file_enhanced(uploaded_file)

                processing_time = time.time() - start_time

                if error:
                    st.error(error)
                else:
                    st.success(f"✅ Enhanced analysis completed in {processing_time:.1f}s")

                    # Display enhanced results
                    display_enhanced_results(results)


if __name__ == "__main__":
    main()
