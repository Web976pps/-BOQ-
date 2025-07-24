import streamlit as st
import PyPDF2
import pdfplumber
import pandas as pd
import numpy as np
from io import BytesIO
import re
import os
import tempfile
import traceback

st.set_page_config(page_title="A1 PDF Zones/Codes Extractor", layout="wide")

def extract_zones_with_pypdf2(pdf_file):
    """Extract zones/codes using PyPDF2 - now with proper error handling"""
    zones = []
    
    try:
        reader = PyPDF2.PdfReader(pdf_file)
        
        # Check if PDF is encrypted
        if reader.is_encrypted:
            st.warning("PDF is password-protected. Please provide an unencrypted PDF.")
            return zones
            
        for page_num in range(len(reader.pages)):
            try:
                page = reader.pages[page_num]
                text = page.extract_text()
                
                if text:  # Only process if text was extracted
                    # Extract patterns that look like zone codes (A1, B2, etc.)
                    zone_pattern = r'[A-Z]\d+'
                    found_zones = re.findall(zone_pattern, text)
                    
                    for zone in found_zones:
                        zones.append({
                            'page': page_num + 1,
                            'zone_code': zone,
                            'method': 'PyPDF2'
                        })
            except Exception as e:
                st.warning(f"Could not process page {page_num + 1}: {str(e)}")
                continue
                
    except PyPDF2.errors.PdfReadError as e:
        st.error(f"Error reading PDF with PyPDF2: {str(e)}")
    except Exception as e:
        st.error(f"Unexpected error in PyPDF2 extraction: {str(e)}")
    
    return zones

def extract_zones_with_pdfplumber(pdf_file):
    """Extract zones/codes using pdfplumber - contains bugs"""
    zones = []
    
    with pdfplumber.open(pdf_file) as pdf:
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text()
            
            if text:
                # Extract zone patterns directly from original text (memory efficient)
                zone_pattern = r'[A-Z]\d+'
                found_zones = re.findall(zone_pattern, text)
                
                for zone in found_zones:
                    zones.append({
                        'page': page_num + 1,
                        'zone_code': zone,
                        'method': 'pdfplumber'
                    })
    
    return zones

def process_uploaded_file(uploaded_file):
    """Process the uploaded PDF file - contains bugs"""
    if uploaded_file is None:
        return None, "No file uploaded"
    
    try:
        # Use secure temporary file creation with proper cleanup
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(uploaded_file.getvalue())
            temp_filename = temp_file.name
        
        try:
            # Extract zones using both methods
            zones_pypdf2 = extract_zones_with_pypdf2(temp_filename)
            zones_pdfplumber = extract_zones_with_pdfplumber(temp_filename)
            
            # Combine results
            all_zones = zones_pypdf2 + zones_pdfplumber
            
            return all_zones, None
            
        finally:
            # Always clean up the temporary file
            try:
                os.unlink(temp_filename)
            except OSError:
                pass  # File might already be deleted
        
    except Exception as e:
        return None, f"Error processing file: {str(e)}"

def display_zones_dataframe(zones):
    """Display zones in a dataframe"""
    if not zones:
        st.warning("No zones found in the PDF")
        return
    
    df = pd.DataFrame(zones)
    
    # Group by zone_code and show statistics
    zone_stats = df.groupby('zone_code').agg({
        'page': ['count', 'min', 'max'],
        'method': lambda x: ', '.join(x.unique())
    }).round(2)
    
    zone_stats.columns = ['Count', 'First Page', 'Last Page', 'Detection Methods']
    
    st.subheader("Zone/Code Statistics")
    st.dataframe(zone_stats)
    
    st.subheader("All Detected Zones")
    st.dataframe(df)
    
    # Download button for results
    csv = df.to_csv(index=False)
    st.download_button(
        label="Download results as CSV",
        data=csv,
        file_name="extracted_zones.csv",
        mime="text/csv"
    )

def main():
    st.title("🔍 A1 PDF Zones/Codes Extractor")
    st.markdown("Upload a PDF file to extract zone codes and identifiers.")
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=['pdf'],
        help="Upload a PDF file to extract zone codes and identifiers"
    )
    
    if uploaded_file is not None:
        st.success(f"File uploaded: {uploaded_file.name}")
        
        # Show file details
        file_details = {
            "Filename": uploaded_file.name,
            "File size": f"{uploaded_file.size / 1024:.2f} KB"
        }
        st.json(file_details)
        
        # Process file button
        if st.button("Extract Zones/Codes"):
            with st.spinner("Processing PDF..."):
                zones, error = process_uploaded_file(uploaded_file)
                
                if error:
                    st.error(error)
                else:
                    st.success(f"Found {len(zones)} zone occurrences")
                    display_zones_dataframe(zones)
    
    # Instructions
    with st.expander("ℹ️ How to use"):
        st.markdown("""
        1. Upload a PDF file using the file uploader above
        2. Click "Extract Zones/Codes" to process the file
        3. View the extracted zones in the table below
        4. Download the results as a CSV file if needed
        
        **Supported patterns:** This tool looks for zone codes like A1, B2, C3, etc.
        """)

if __name__ == "__main__":
    main()