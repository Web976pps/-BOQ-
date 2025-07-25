#!/usr/bin/env python3
"""
Create a realistic architectural test PDF with zones and furniture codes
"""


from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def create_architectural_test_pdf():
    """Create a test PDF with realistic architectural zones and furniture codes"""
    filename = "architectural_test.pdf"

    # Create PDF with A4 page size
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    # Page 1 - Floor Plan with Zones
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "ARCHITECTURAL FLOOR PLAN - LEVEL 1")

    c.setFont("Helvetica", 12)
    c.drawString(50, height - 80, "Project: Innovation Center | Drawing: A1-001 | Scale: 1:100")

    # Zone Labels (ALL CAPS as required)
    zones_page1 = [
        ("INNOVATION HUB", 100, height - 150),
        ("COLLABORATION SPACE", 300, height - 150),
        ("MEETING ROOM", 500, height - 150),
        ("KITCHEN", 100, height - 250),
        ("EAT", 200, height - 250),
        ("CREATE", 300, height - 250),
        ("WORK SPACE", 450, height - 250),
        ("STORAGE", 100, height - 350),
        ("RECEPTION", 300, height - 350),
    ]

    c.setFont("Helvetica-Bold", 14)
    for zone, x, y in zones_page1:
        c.drawString(x, y, zone)

    # Furniture Codes for Page 1
    furniture_codes_page1 = [
        # Chairs (CH prefix)
        ("CH15", 120, height - 180),
        ("CH15A", 140, height - 180),
        ("CH21", 320, height - 180),
        ("CH21 b", 340, height - 180),
        # Tables (TB prefix)
        ("TB01", 520, height - 180),
        ("TB02", 540, height - 180),
        ("TB03A", 120, height - 280),
        # Counters (C prefix)
        ("C101", 220, height - 280),
        ("C102", 240, height - 280),
        # Storage Units (SU prefix)
        ("SU05", 120, height - 380),
        ("SU06A", 140, height - 380),
        # Kitchen items (KT prefix)
        ("KT01", 470, height - 280),
        ("KT02 a", 490, height - 280),
    ]

    c.setFont("Helvetica", 10)
    for code, x, y in furniture_codes_page1:
        c.drawString(x, y, code)

    # Add some architectural drawing elements
    c.setStrokeGray(0.5)
    c.setLineWidth(1)

    # Draw some basic room outlines
    c.rect(80, height - 200, 180, 80)  # Innovation Hub
    c.rect(280, height - 200, 180, 80)  # Collaboration Space
    c.rect(480, height - 200, 100, 80)  # Meeting Room
    c.rect(80, height - 300, 100, 80)  # Kitchen
    c.rect(200, height - 300, 80, 80)  # Eat
    c.rect(280, height - 300, 80, 80)  # Create

    # Page 2 - Another floor with different zones
    c.showPage()

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "ARCHITECTURAL FLOOR PLAN - LEVEL 2")

    c.setFont("Helvetica", 12)
    c.drawString(50, height - 80, "Project: Innovation Center | Drawing: A1-002 | Scale: 1:100")

    # More zones for page 2
    zones_page2 = [
        ("CONFERENCE", 100, height - 150),
        ("BREAK OUT", 300, height - 150),
        ("QUIET ZONE", 500, height - 150),
        ("COPY AREA", 100, height - 250),
        ("ARCHIVE", 250, height - 250),
        ("SERVER ROOM", 400, height - 250),
        ("LOUNGE", 100, height - 350),
        ("PANTRY", 300, height - 350),
    ]

    c.setFont("Helvetica-Bold", 14)
    for zone, x, y in zones_page2:
        c.drawString(x, y, zone)

    # More furniture codes for page 2
    furniture_codes_page2 = [
        # More chairs with variations
        ("CH25", 120, height - 180),
        ("CH25A", 140, height - 180),
        ("CH30 b", 160, height - 180),
        ("CH31", 320, height - 180),
        # More tables
        ("TB10", 520, height - 180),
        ("TB11A", 540, height - 180),
        ("TB12", 120, height - 280),
        # Cabinets and storage
        ("C201", 270, height - 280),
        ("C202 a", 290, height - 280),
        ("SU10", 420, height - 280),
        ("SU11", 440, height - 280),
        # Kitchen equipment
        ("KT10", 120, height - 380),
        ("KT11A", 140, height - 380),
        ("KT12", 320, height - 380),
    ]

    c.setFont("Helvetica", 10)
    for code, x, y in furniture_codes_page2:
        c.drawString(x, y, code)

    # Add legend
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, 100, "FURNITURE CODE LEGEND:")

    c.setFont("Helvetica", 10)
    legend_items = [
        "CH = Chair",
        "TB = Table",
        "C = Counter/Cabinet",
        "SU = Storage Unit",
        "KT = Kitchen Equipment",
    ]

    for i, item in enumerate(legend_items):
        c.drawString(50, 80 - (i * 15), item)

    # Zone legend
    c.setFont("Helvetica-Bold", 12)
    c.drawString(300, 100, "ZONE TYPES:")

    c.setFont("Helvetica", 10)
    zone_legend = [
        "ALL CAPS = Zone/Area Labels",
        "Mixed codes = Furniture Items",
        "Numbers/Letters = Variations",
    ]

    for i, item in enumerate(zone_legend):
        c.drawString(300, 80 - (i * 15), item)

    # Save the PDF
    c.save()

    print(f"✅ Created test PDF: {filename}")
    print("📊 Contains:")
    print(f"   - {len(zones_page1 + zones_page2)} zone labels")
    print(f"   - {len(furniture_codes_page1 + furniture_codes_page2)} furniture codes")
    print("   - 2 pages with realistic architectural layout")

    return filename


if __name__ == "__main__":
    create_architectural_test_pdf()
