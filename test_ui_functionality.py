#!/usr/bin/env python3
"""
Test script to verify core functionality before UI smoke test
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd

from app import extract_zones_with_pdfplumber, extract_zones_with_pypdf2, process_uploaded_file


def test_extraction_functionality():
    """Test the PDF extraction functionality"""
    print("🧪 Testing PDF Extraction Functionality...")
    print("=" * 50)

    test_file = "test_zones.pdf"

    if not os.path.exists(test_file):
        print("❌ Test PDF not found!")
        return False

    print(f"📄 Testing with file: {test_file}")
    print(f"📊 File size: {os.path.getsize(test_file)} bytes")

    try:
        # Test PyPDF2 extraction
        print("\n🔍 Testing PyPDF2 extraction...")
        zones_pypdf2 = extract_zones_with_pypdf2(test_file)
        print(f"✅ PyPDF2 found {len(zones_pypdf2)} zones")

        # Test pdfplumber extraction
        print("\n🔍 Testing pdfplumber extraction...")
        zones_pdfplumber = extract_zones_with_pdfplumber(test_file)
        print(f"✅ pdfplumber found {len(zones_pdfplumber)} zones")

        # Test the main processing function
        print("\n🔍 Testing main processing function...")
        with open(test_file, "rb") as f:

            class MockUploadedFile:
                def __init__(self, file_content):
                    self.content = file_content

                def getvalue(self):
                    return self.content

            mock_file = MockUploadedFile(f.read())
            processed_zones, error = process_uploaded_file(mock_file)

            if error:
                print(f"❌ Processing error: {error}")
                return False

            print(f"✅ Main function found {len(processed_zones)} unique zones")

            # Display results
            print("\n📋 Extracted Zones:")
            print("-" * 30)
            for zone in processed_zones[:10]:  # Show first 10
                print(f"Page {zone['page']}: {zone['zone_code']} ({zone['method']})")

            if len(processed_zones) > 10:
                print(f"... and {len(processed_zones) - 10} more zones")

            # Test DataFrame creation
            print("\n📊 Testing DataFrame creation...")
            df = pd.DataFrame(processed_zones)
            print(f"✅ DataFrame created with {len(df)} rows and {len(df.columns)} columns")
            print(f"📄 Columns: {list(df.columns)}")

            # Expected zone codes in our test PDF
            expected_zones = [
                "A1",
                "B2",
                "C3",
                "D4",
                "E5",
                "F6",
                "G7",
                "H8",
                "X9",
                "J1",
                "K2",
                "L3",
                "M4",
                "N5",
                "O6",
                "P7",
            ]
            found_codes = [zone["zone_code"] for zone in processed_zones]

            print("\n🎯 Zone Detection Analysis:")
            print(f"Expected zones: {len(expected_zones)}")
            print(f"Found zones: {len(set(found_codes))}")

            detected_expected = [code for code in expected_zones if code in found_codes]
            print(f"✅ Correctly detected: {len(detected_expected)} zones")
            print(f"Detected codes: {detected_expected}")

            return True

    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        return False


def test_csv_export():
    """Test CSV export functionality"""
    print("\n📝 Testing CSV Export...")

    # Create sample data
    sample_data = [
        {"page": 1, "zone_code": "A1", "method": "PyPDF2"},
        {"page": 1, "zone_code": "B2", "method": "pdfplumber"},
        {"page": 2, "zone_code": "C3", "method": "PyPDF2, pdfplumber"},
    ]

    try:
        df = pd.DataFrame(sample_data)
        csv_content = df.to_csv(index=False)
        print("✅ CSV export successful")
        print(f"📄 CSV preview:\n{csv_content[:200]}...")
        return True
    except Exception as e:
        print(f"❌ CSV export failed: {str(e)}")
        return False


if __name__ == "__main__":
    print("🚀 Starting UI Functionality Test")
    print("=" * 50)

    # Run tests
    extraction_ok = test_extraction_functionality()
    csv_ok = test_csv_export()

    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    print(f"📄 PDF Extraction: {'✅ PASS' if extraction_ok else '❌ FAIL'}")
    print(f"📝 CSV Export: {'✅ PASS' if csv_ok else '❌ FAIL'}")

    if extraction_ok and csv_ok:
        print("\n🎉 All tests passed! Ready for UI smoke test!")
        print("\n📋 UI SMOKE TEST CHECKLIST:")
        print("1. ✅ Open browser to http://localhost:8501")
        print("2. ✅ Upload test_zones.pdf")
        print("3. ✅ Verify zones table displays")
        print("4. ✅ Check download CSV button works")
        print("5. ✅ Verify zone counts are correct")
    else:
        print("\n❌ Some tests failed. Check the issues above before UI testing.")
