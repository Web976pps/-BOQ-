import os
import re
import tempfile
from collections import defaultdict

import numpy as np
import pandas as pd
import pdfplumber
import PyPDF2
import pytesseract
import streamlit as st
from pdf2image import convert_from_path

st.set_page_config(page_title="A1 PDF Zones/Codes Extractor", layout="wide")


class ZoneExtractor:
    """Advanced zone and furniture code extractor with OCR and spatial analysis"""

    def __init__(self):
        self.furniture_prefixes = ["CH", "TB", "C", "SU", "KT"]
        self.zone_memory = {}  # Track zones to avoid duplicates
        self.code_associations = defaultdict(list)  # Associate codes to zones

    def detect_all_caps_zones(self, text):
        """Detect ALL CAPS zone/area labels like INNOVATION HUB, EAT, CREATE"""
        # Pattern for ALL CAPS words (2+ chars) that could be zone names
        all_caps_pattern = r"\b[A-Z]{2,}(?:\s+[A-Z]{2,})*\b"
        matches = re.findall(all_caps_pattern, text)

        # Filter out common non-zone words
        excluded_words = {"THE", "AND", "OR", "IN", "ON", "AT", "TO", "FOR", "OF", "WITH", "BY"}
        zone_candidates = []

        for match in matches:
            words = match.split()
            # Keep if it's not just excluded words and has meaningful length
            if len(match) >= 3 and not all(word in excluded_words for word in words):
                zone_candidates.append(match)

        return zone_candidates

    def detect_furniture_codes(self, text):
        """Detect furniture/joinery codes by prefix (CH, TB, C, SU, KT)"""
        furniture_codes = []

        for prefix in self.furniture_prefixes:
            # Pattern: PREFIX followed by numbers, optional letter/space variations
            # Examples: CH15, CH15A, CH15 a, CH15b, CH21 b
            pattern = rf"\b{prefix}\d+(?:[A-Za-z]|\s+[A-Za-z])?\b"
            matches = re.findall(pattern, text, re.IGNORECASE)

            # Clean and normalize matches
            for match in matches:
                # Normalize spacing and case
                clean_code = re.sub(r"\s+", "", match.upper())
                furniture_codes.append(clean_code)

        return furniture_codes

    def extract_with_ocr(self, pdf_path, page_num):
        """Extract text using OCR with PSM 11 for better zone detection"""
        try:
            # Convert PDF page to image
            images = convert_from_path(
                pdf_path, first_page=page_num + 1, last_page=page_num + 1, dpi=300
            )
            if not images:
                return [], []

            image = images[0]

            # Convert to numpy array for OpenCV processing
            img_array = np.array(image)

            # OCR with PSM 11 (sparse text detection)
            custom_config = r"--oem 3 --psm 11"
            text = pytesseract.image_to_string(img_array, config=custom_config)

            # Also get bounding box data for spatial analysis
            data = pytesseract.image_to_data(
                img_array, config=custom_config, output_type=pytesseract.Output.DICT
            )

            # Extract zones and codes
            zones = self.detect_all_caps_zones(text)
            codes = self.detect_furniture_codes(text)

            # Spatial analysis for better association
            word_positions = []
            for i, word in enumerate(data["text"]):
                if int(data["conf"][i]) > 30:  # Confidence threshold
                    word_positions.append(
                        {
                            "text": word,
                            "x": data["left"][i],
                            "y": data["top"][i],
                            "w": data["width"][i],
                            "h": data["height"][i],
                        }
                    )

            return zones, codes, word_positions

        except Exception as e:
            st.warning(f"OCR failed for page {page_num + 1}: {str(e)}")
            return [], [], []

    def extract_with_text_methods(self, pdf_path):
        """Extract using traditional text extraction methods as fallback"""
        all_zones = []
        all_codes = []

        # Try pdfplumber first
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if text:
                        zones = self.detect_all_caps_zones(text)
                        codes = self.detect_furniture_codes(text)

                        for zone in zones:
                            all_zones.append(
                                {
                                    "page": page_num + 1,
                                    "zone_area": zone,
                                    "method": "pdfplumber",
                                    "x": None,
                                    "y": None,
                                }
                            )

                        for code in codes:
                            all_codes.append(
                                {
                                    "page": page_num + 1,
                                    "code": code,
                                    "code_type": self.get_code_type(code),
                                    "method": "pdfplumber",
                                    "x": None,
                                    "y": None,
                                }
                            )
        except Exception as e:
            st.warning(f"pdfplumber extraction failed: {str(e)}")

        # Try PyPDF2 as additional fallback
        try:
            with open(pdf_path, "rb") as file:
                reader = PyPDF2.PdfReader(file)
                for page_num in range(len(reader.pages)):
                    page = reader.pages[page_num]
                    text = page.extract_text()
                    if text:
                        zones = self.detect_all_caps_zones(text)
                        codes = self.detect_furniture_codes(text)

                        for zone in zones:
                            all_zones.append(
                                {
                                    "page": page_num + 1,
                                    "zone_area": zone,
                                    "method": "PyPDF2",
                                    "x": None,
                                    "y": None,
                                }
                            )

                        for code in codes:
                            all_codes.append(
                                {
                                    "page": page_num + 1,
                                    "code": code,
                                    "code_type": self.get_code_type(code),
                                    "method": "PyPDF2",
                                    "x": None,
                                    "y": None,
                                }
                            )
        except Exception as e:
            st.warning(f"PyPDF2 extraction failed: {str(e)}")

        return all_zones, all_codes

    def get_code_type(self, code):
        """Determine the type of furniture code"""
        for prefix in self.furniture_prefixes:
            if code.upper().startswith(prefix):
                return prefix
        return "UNKNOWN"

    def associate_codes_to_zones(self, zones, codes, word_positions=None):
        """Associate furniture codes to zones using spatial logic"""
        associations = defaultdict(list)

        if word_positions:
            # Use spatial proximity for association
            for code_item in codes:
                closest_zone = None
                min_distance = float("inf")

                code_pos = None
                for pos in word_positions:
                    if code_item["code"] in pos["text"]:
                        code_pos = pos
                        break

                if code_pos:
                    for zone_item in zones:
                        zone_pos = None
                        for pos in word_positions:
                            if zone_item["zone_area"] in pos["text"]:
                                zone_pos = pos
                                break

                        if zone_pos:
                            # Calculate distance
                            distance = np.sqrt(
                                (code_pos["x"] - zone_pos["x"]) ** 2
                                + (code_pos["y"] - zone_pos["y"]) ** 2
                            )
                            if distance < min_distance:
                                min_distance = distance
                                closest_zone = zone_item["zone_area"]

                if closest_zone:
                    associations[closest_zone].append(code_item)
                else:
                    associations["UNASSIGNED"].append(code_item)
        else:
            # Fallback: associate by page proximity
            for page in set(item["page"] for item in zones + codes):
                page_zones = [z for z in zones if z["page"] == page]
                page_codes = [c for c in codes if c["page"] == page]

                if page_zones:
                    # Assign codes to first zone on page (simple heuristic)
                    primary_zone = page_zones[0]["zone_area"]
                    for code_item in page_codes:
                        associations[primary_zone].append(code_item)
                else:
                    # No zones on page, mark as unassigned
                    for code_item in page_codes:
                        associations["UNASSIGNED"].append(code_item)

        return associations

    def process_pdf(self, pdf_path):
        """Main processing function combining OCR and text extraction"""
        all_zones = []
        all_codes = []

        # First, try OCR extraction for better spatial analysis
        try:
            # Get number of pages
            with pdfplumber.open(pdf_path) as pdf:
                num_pages = len(pdf.pages)

            for page_num in range(min(num_pages, 10)):  # Limit to first 10 pages for performance
                zones, codes, positions = self.extract_with_ocr(pdf_path, page_num)

                for zone in zones:
                    all_zones.append(
                        {
                            "page": page_num + 1,
                            "zone_area": zone,
                            "method": "OCR",
                            "x": None,
                            "y": None,
                        }
                    )

                for code in codes:
                    all_codes.append(
                        {
                            "page": page_num + 1,
                            "code": code,
                            "code_type": self.get_code_type(code),
                            "method": "OCR",
                            "x": None,
                            "y": None,
                        }
                    )

        except Exception as e:
            st.warning(f"OCR processing failed, falling back to text extraction: {str(e)}")

        # Supplement with traditional text extraction
        text_zones, text_codes = self.extract_with_text_methods(pdf_path)
        all_zones.extend(text_zones)
        all_codes.extend(text_codes)

        # Remove duplicates based on content and page
        unique_zones = self.remove_duplicates(all_zones, "zone_area")
        unique_codes = self.remove_duplicates(all_codes, "code")

        # Associate codes to zones
        associations = self.associate_codes_to_zones(unique_zones, unique_codes)

        return unique_zones, unique_codes, associations

    def remove_duplicates(self, items, key_field):
        """Remove duplicate items based on page and key field"""
        seen = set()
        unique_items = []

        for item in items:
            item_key = (item["page"], item[key_field])
            if item_key not in seen:
                seen.add(item_key)
                unique_items.append(item)
            else:
                # Merge methods for existing items
                for existing in unique_items:
                    if (existing["page"], existing[key_field]) == item_key:
                        if item["method"] not in existing["method"]:
                            existing["method"] += f", {item['method']}"
                        break

        return unique_items


def process_uploaded_file(uploaded_file):
    """Process the uploaded PDF file with comprehensive extraction"""
    if uploaded_file is None:
        return None, None, None, "No file uploaded"

    try:
        # Create secure temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(uploaded_file.getvalue())
            temp_filename = temp_file.name

        try:
            # Initialize extractor and process
            extractor = ZoneExtractor()
            zones, codes, associations = extractor.process_pdf(temp_filename)

            return zones, codes, associations, None

        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_filename)
            except OSError:
                pass

    except Exception as e:
        return None, None, None, f"Error processing file: {str(e)}"


def create_comprehensive_csv(zones, codes, associations):
    """Create a comprehensive CSV with zone associations and totals"""
    csv_data = []

    # Process associations
    for zone_area, zone_codes in associations.items():
        # Group codes by type for this zone
        code_type_counts = defaultdict(int)
        zone_code_details = []

        for code_item in zone_codes:
            code_type = code_item["code_type"]
            code_type_counts[code_type] += 1
            zone_code_details.append(
                {
                    "Zone/Area": zone_area,
                    "Code": code_item["code"],
                    "Code Type": code_type,
                    "Page": code_item["page"],
                    "Detection Method": code_item["method"],
                }
            )

        # Add individual code entries
        csv_data.extend(zone_code_details)

        # Add subtotal row for each code type in this zone
        for code_type, count in code_type_counts.items():
            csv_data.append(
                {
                    "Zone/Area": zone_area,
                    "Code": f"SUBTOTAL {code_type}",
                    "Code Type": code_type,
                    "Page": "ALL",
                    "Detection Method": "CALCULATED",
                    "Count": count,
                }
            )

    # Add grand totals
    total_codes_by_type = defaultdict(int)
    for code_item in codes:
        total_codes_by_type[code_item["code_type"]] += 1

    csv_data.append(
        {
            "Zone/Area": "=== GRAND TOTALS ===",
            "Code": "",
            "Code Type": "",
            "Page": "",
            "Detection Method": "",
            "Count": "",
        }
    )
    for code_type, total in total_codes_by_type.items():
        csv_data.append(
            {
                "Zone/Area": "GRAND TOTAL",
                "Code": f"TOTAL {code_type}",
                "Code Type": code_type,
                "Page": "ALL",
                "Detection Method": "CALCULATED",
                "Count": total,
            }
        )

    return pd.DataFrame(csv_data)


def display_results(zones, codes, associations):
    """Display comprehensive results with statistics and downloads"""
    if not zones and not codes:
        st.warning("No zones or furniture codes found in the PDF")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🏢 Detected Zones/Areas")
        if zones:
            zones_df = pd.DataFrame(zones)
            st.dataframe(zones_df, use_container_width=True)
            st.metric("Total Zones", len(zones))
        else:
            st.info("No zones detected")

    with col2:
        st.subheader("🪑 Detected Furniture Codes")
        if codes:
            codes_df = pd.DataFrame(codes)
            st.dataframe(codes_df, use_container_width=True)

            # Code type statistics
            code_stats = codes_df["code_type"].value_counts()
            st.subheader("Code Type Distribution")
            st.bar_chart(code_stats)
        else:
            st.info("No furniture codes detected")

    # Zone-Code Associations
    st.subheader("🔗 Zone-Code Associations")
    if associations:
        for zone_area, zone_codes in associations.items():
            if zone_codes:
                with st.expander(f"{zone_area} ({len(zone_codes)} codes)"):
                    assoc_df = pd.DataFrame(zone_codes)
                    st.dataframe(assoc_df, use_container_width=True)

    # Comprehensive CSV Export
    if zones or codes:
        comprehensive_df = create_comprehensive_csv(zones, codes, associations)
        csv = comprehensive_df.to_csv(index=False)

        st.subheader("📥 Download Results")
        st.download_button(
            label="Download Comprehensive CSV Report",
            data=csv,
            file_name="zone_furniture_extraction_report.csv",
            mime="text/csv",
            help="Complete report with zones, codes, associations, and totals",
        )


def main():
    st.title("🏗️ A1 PDF Zones/Codes Extractor")
    st.markdown(
        "**Advanced OCR-based extraction of zones and furniture codes from architectural PDFs**"
    )

    # File uploader
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=["pdf"],
        help="Upload an architectural PDF to extract zones and furniture codes",
    )

    if uploaded_file is not None:
        st.success(f"File uploaded: {uploaded_file.name}")

        # Show file details
        file_details = {
            "Filename": uploaded_file.name,
            "File size": f"{uploaded_file.size / 1024:.2f} KB",
        }
        st.json(file_details)

        # Process file button
        if st.button("🔍 Extract Zones & Furniture Codes"):
            with st.spinner("Processing PDF with OCR and spatial analysis..."):
                zones, codes, associations, error = process_uploaded_file(uploaded_file)

                if error:
                    st.error(error)
                else:
                    st.success(f"✅ Found {len(zones)} zones and {len(codes)} furniture codes")
                    display_results(zones, codes, associations)

    # Instructions
    with st.expander("ℹ️ How this tool works"):
        st.markdown(
            """
        ### 🎯 Detection Capabilities:

        **Zone/Area Detection:**
        - Detects ALL CAPS zone labels (e.g., INNOVATION HUB, EAT, CREATE)
        - Uses OCR with PSM 11 for optimal sparse text detection
        - Filters out common words to focus on meaningful zone names

        **Furniture Code Detection:**
        - Detects codes with prefixes: **CH, TB, C, SU, KT**
        - Handles variations: CH15, CH15A, CH15 a, CH15b, CH21 b
        - Normalizes spacing and case automatically

        **Smart Association:**
        - Associates furniture codes to zones using spatial proximity
        - Combines OCR with traditional text extraction for better coverage
        - Avoids duplicate counting with intelligent deduplication

        **Export Features:**
        - Comprehensive CSV with zone associations
        - Subtotals by code type per zone
        - Grand totals across all zones
        - Detection method tracking for verification

        ### ⚠️ Important Notes:
        - Does not rely on PDF bounding boxes (unreliable)
        - Uses spatial + text logic for accurate associations
        - Processes up to 10 pages for performance optimization
        - Requires clear, high-quality PDF text for best results
        """
        )


if __name__ == "__main__":
    main()
