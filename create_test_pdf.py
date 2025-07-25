#!/usr/bin/env python3
"""
Simple script to create a test PDF with zone codes for UI testing
"""


from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def create_test_pdf():
    """Create a test PDF with sample zone codes"""
    filename = "test_zones.pdf"

    # Create PDF
    c = canvas.Canvas(filename, pagesize=letter)

    # Page 1
    c.drawString(100, 750, "A1 PDF Zones/Codes Extractor - Test Document")
    c.drawString(100, 700, "This document contains sample zone codes for testing:")
    c.drawString(100, 650, "Zone A1: Residential Area North")
    c.drawString(100, 600, "Zone B2: Commercial District")
    c.drawString(100, 550, "Zone C3: Industrial Zone")
    c.drawString(100, 500, "Zone D4: Mixed Use Development")
    c.drawString(100, 450, "Zone E5: Agricultural Land")
    c.drawString(100, 400, "Additional codes: F6, G7, H8")
    c.drawString(100, 350, "Special designation: X9 (Reserved)")

    # Page 2
    c.showPage()
    c.drawString(100, 750, "Page 2 - Additional Zone Information")
    c.drawString(100, 700, "More zone codes:")
    c.drawString(100, 650, "Zone J1: Public Services")
    c.drawString(100, 600, "Zone K2: Transportation Hub")
    c.drawString(100, 550, "Zone L3: Educational District")
    c.drawString(100, 500, "Zone M4: Healthcare Zone")
    c.drawString(100, 450, "Complex patterns: N5-A, O6-B, P7-C")

    c.save()
    print(f"Test PDF created: {filename}")
    return filename


if __name__ == "__main__":
    create_test_pdf()
