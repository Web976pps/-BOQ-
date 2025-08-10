# path: src/ui/streamlit_app.py
import os
import sys
import tempfile
import time

import pandas as pd
import streamlit as st

# Add the workspace to Python path to import enhanced functionality
sys.path.insert(0, "/workspace")

# Apply PIL image size fix before importing enhanced functionality
try:
    from PIL import Image, ImageFile

    Image.MAX_IMAGE_PIXELS = None  # Remove PIL image size limit
    ImageFile.LOAD_TRUNCATED_IMAGES = True  # Handle truncated images
except ImportError:
    pass  # PIL might not be available

try:
    from enhanced_app import EnhancedZoneExtractor

    ENHANCED_AVAILABLE = True
except ImportError:
    ENHANCED_AVAILABLE = False

st.set_page_config(page_title="-BOQ- Zones/Codes Extractor", layout="wide")
st.title("A1 PDF Zones/Codes Extractor (-BOQ-)")

# Add status indicator
if ENHANCED_AVAILABLE:
    st.success("✅ Enhanced extraction pipeline available")
else:
    st.warning("⚠️ Using fallback processing")

uploaded = st.file_uploader("Upload an A1 PDF", type=["pdf"])
run_btn = st.button("Run Enhanced Extraction", disabled=uploaded is None)

if run_btn and uploaded:
    if not ENHANCED_AVAILABLE:
        st.error("❌ Enhanced extraction not available. Please check system configuration.")
        st.stop()

    with st.spinner("🔍 Processing PDF with enhanced extraction..."):
        # Create temporary file for processing
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_file.write(uploaded.read())
            temp_file.flush()
            temp_pdf_path = temp_file.name

        try:
            # Initialize enhanced extractor
            extractor = EnhancedZoneExtractor()

            # Process the PDF
            start_time = time.time()
            results = extractor.process_pdf_enhanced(temp_pdf_path)
            processing_time = time.time() - start_time

            # Clean up temp file
            os.unlink(temp_pdf_path)

            if results:
                st.success(f"✅ Processing completed in {processing_time:.2f} seconds")

                # Extract data for display
                zones = results.get("zones", [])
                codes = results.get("codes", [])
                validation = results.get("validation", {})

                st.write(f"📊 **Results Summary**: {len(zones)} zones, {len(codes)} codes detected")

                # Create the four tables in the same format as the original UI

                # 1. Row-level instances (individual detections)
                row_level_data = []
                for i, zone in enumerate(zones):
                    row_level_data.append(
                        {
                            "Type": "Zone",
                            "Text": zone.get("text", f"Zone_{i+1}"),
                            "Confidence": zone.get("confidence", 0),
                            "Page": 1,
                            "X": zone.get("bbox", {}).get("x1", 0),
                            "Y": zone.get("bbox", {}).get("y1", 0),
                        }
                    )

                for i, code in enumerate(codes):
                    row_level_data.append(
                        {
                            "Type": "Code",
                            "Text": code.get("text", f"Code_{i+1}"),
                            "Confidence": code.get("confidence", 0),
                            "Page": 1,
                            "X": code.get("bbox", {}).get("x1", 0),
                            "Y": code.get("bbox", {}).get("y1", 0),
                        }
                    )

                # 2. Unique zone-code combinations
                unique_data = []
                zone_texts = [zone.get("text", f"Zone_{i+1}") for i, zone in enumerate(zones)]
                code_texts = [code.get("text", f"Code_{i+1}") for i, code in enumerate(codes)]

                for zone_text in zone_texts:
                    for code_text in code_texts:
                        unique_data.append({"Zone": zone_text, "Code": code_text, "Count": 1})

                # 3. Zone x Prefix summary
                zone_prefix_data = []
                for zone_text in zone_texts:
                    # Count codes by prefix for this zone
                    prefix_counts = {}
                    for code in codes:
                        code_text = code.get("text", "")
                        for prefix in ["CH", "TB", "C", "SU", "KT", "SK", "FL"]:
                            if code_text.startswith(prefix):
                                prefix_counts[prefix] = prefix_counts.get(prefix, 0) + 1
                                break

                    for prefix, count in prefix_counts.items():
                        zone_prefix_data.append(
                            {"Zone": zone_text, "Prefix": prefix, "Count": count}
                        )

                # 4. Global prefix summary
                global_prefix_data = []
                global_prefix_counts = {}
                for code in codes:
                    code_text = code.get("text", "")
                    for prefix in ["CH", "TB", "C", "SU", "KT", "SK", "FL"]:
                        if code_text.startswith(prefix):
                            global_prefix_counts[prefix] = global_prefix_counts.get(prefix, 0) + 1
                            break

                for prefix, count in global_prefix_counts.items():
                    global_prefix_data.append({"Prefix": prefix, "Total_Count": count})

                # Convert to DataFrames
                row_df = pd.DataFrame(row_level_data)
                unique_df = pd.DataFrame(unique_data)
                zone_prefix_df = pd.DataFrame(zone_prefix_data)
                global_prefix_df = pd.DataFrame(global_prefix_data)

                # Display in tabs (same as original UI)
                tabs = st.tabs(["Instances", "Unique", "Zone x Prefix", "Global Prefix"])

                with tabs[0]:
                    st.subheader("Row-Level Instances")
                    st.dataframe(row_df)
                    st.download_button(
                        "Download row_level_instances.csv",
                        data=row_df.to_csv(index=False),
                        file_name="row_level_instances.csv",
                        mime="text/csv",
                    )

                with tabs[1]:
                    st.subheader("Unique Zone-Code Combinations")
                    st.dataframe(unique_df)
                    st.download_button(
                        "Download unique_zone_codes.csv",
                        data=unique_df.to_csv(index=False),
                        file_name="unique_zone_codes.csv",
                        mime="text/csv",
                    )

                with tabs[2]:
                    st.subheader("Zone x Prefix Summary")
                    st.dataframe(zone_prefix_df)
                    st.download_button(
                        "Download zone_prefix_summary.csv",
                        data=zone_prefix_df.to_csv(index=False),
                        file_name="zone_prefix_summary.csv",
                        mime="text/csv",
                    )

                with tabs[3]:
                    st.subheader("Global Prefix Summary")
                    st.dataframe(global_prefix_df)
                    st.download_button(
                        "Download global_prefix_summary.csv",
                        data=global_prefix_df.to_csv(index=False),
                        file_name="global_prefix_summary.csv",
                        mime="text/csv",
                    )

                # Additional enhanced information
                if validation:
                    st.subheader("🔍 Enhanced Processing Information")
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric("Total Zones", validation.get("total_zones", len(zones)))
                    with col2:
                        st.metric("Zones with Codes", validation.get("zones_with_codes", 0))
                    with col3:
                        st.metric("Avg Confidence", f"{validation.get('avg_confidence', 0):.2f}")

                    issues = validation.get("issues", [])
                    if issues:
                        st.subheader("⚠️ Processing Notes")
                        for issue in issues:
                            st.info(f"ℹ️ {issue}")

            else:
                st.error("❌ Processing failed: No results returned")

        except Exception as e:
            # Clean up temp file in case of error
            if os.path.exists(temp_pdf_path):
                os.unlink(temp_pdf_path)
            st.error(f"❌ Processing failed: {str(e)}")
            st.write("**Error details:**")
            st.code(str(e))

# Footer information
st.markdown("---")
st.markdown(
    "**Enhanced A1 PDF Zones/Codes Extractor** - Powered by advanced OCR and geometric analysis"
)
if ENHANCED_AVAILABLE:
    st.markdown(
        "🔧 Using enhanced extraction pipeline with 600 DPI processing, zone memory management, and confidence scoring"
    )
else:
    st.markdown("⚠️ Enhanced features not available - please check system configuration")
