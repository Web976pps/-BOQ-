# path: src/ui/streamlit_app.py
import streamlit as st
import tempfile
from pathlib import Path
import pandas as pd
import subprocess

st.set_page_config(page_title="-BOQ- Zones/Codes Extractor", layout="wide")
st.title("A1 PDF Zones/Codes Extractor (-BOQ-)")

uploaded = st.file_uploader("Upload an A1 PDF", type=["pdf"])
run_btn = st.button("Run Extraction", disabled=uploaded is None)

if run_btn and uploaded:
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / uploaded.name
        with open(pdf_path, "wb") as f:
            f.write(uploaded.read())
        out_dir = Path(tmpdir) / "out"
        out_dir.mkdir(exist_ok=True)

        cmd = [
            "python", "-m", "src.extract_zones_codes",
            "--pdf", str(pdf_path),
            "--out", str(out_dir),
            "--config", "config/default.yml",
        ]
        st.write("Running:", " ".join(cmd))
        subprocess.run(cmd, check=True)

        row_csv  = out_dir / "row_level_instances.csv"
        uniq_csv = out_dir / "unique_zone_codes.csv"
        zone_csv = out_dir / "zone_prefix_summary.csv"
        glob_csv = out_dir / "global_prefix_summary.csv"

        tabs = st.tabs(["Instances", "Unique", "Zone x Prefix", "Global Prefix"])
        with tabs[0]:
            st.dataframe(pd.read_csv(row_csv))
            st.download_button("Download row_level_instances.csv", data=row_csv.read_bytes(), file_name=row_csv.name)
        with tabs[1]:
            st.dataframe(pd.read_csv(uniq_csv))
            st.download_button("Download unique_zone_codes.csv", data=uniq_csv.read_bytes(), file_name=uniq_csv.name)
        with tabs[2]:
            st.dataframe(pd.read_csv(zone_csv))
            st.download_button("Download zone_prefix_summary.csv", data=zone_csv.read_bytes(), file_name=zone_csv.name)
        with tabs[3]:
            st.dataframe(pd.read_csv(glob_csv))
            st.download_button("Download global_prefix_summary.csv", data=glob_csv.read_bytes(), file_name=glob_csv.name)

        # TODO: optionally serve overlay PNGs if generated 