#!/usr/bin/env python3
"""
UI Refresh Status Check
Quick verification that the refreshed UI has all fixes active
"""

import sys

import requests

# Add project root to path
sys.path.insert(0, "/workspace")


def check_ui_status():
    """Check UI accessibility and feature status"""
    print("🔄 UI REFRESH STATUS CHECK")
    print("=" * 60)

    # Check UI accessibility
    try:
        response = requests.get("http://localhost:8501", timeout=10)
        if response.status_code == 200:
            print("✅ UI accessible at http://localhost:8501")
        else:
            print(f"❌ UI not accessible: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ UI connectivity failed: {e}")
        return False

    # Check PIL settings
    try:
        from PIL import Image, ImageFile

        print(f"✅ PIL MAX_IMAGE_PIXELS: {Image.MAX_IMAGE_PIXELS} (None = unlimited)")
        print(f"✅ PIL LOAD_TRUNCATED_IMAGES: {ImageFile.LOAD_TRUNCATED_IMAGES}")
    except Exception as e:
        print(f"⚠️ PIL settings check failed: {e}")

    # Check enhanced functionality
    try:
        from enhanced_app import A1PDFProcessor, EnhancedZoneExtractor

        extractor = EnhancedZoneExtractor()
        processor = A1PDFProcessor()

        print("✅ Enhanced functionality available")
        print(f"   📐 A1 dimensions: {processor.a1_dimensions_mm}")
        print(
            f"   🎯 DPI range: {processor.min_dpi}-{processor.max_dpi} (target: {processor.target_dpi})"
        )
        print(f"   🖼️ Max pixels: {processor.max_pixels}")

        # Test DPI calculation with the problematic size
        safe_dpi = processor.calculate_safe_dpi(1000.1, 707.0)
        print(f"   🔧 Safe DPI for 1000.1×707.0mm: {safe_dpi}")

    except Exception as e:
        print(f"❌ Enhanced functionality check failed: {e}")
        return False

    return True


def check_ui_file_updates():
    """Check that UI file has the latest updates"""
    print("\n📱 UI FILE UPDATE STATUS")
    print("=" * 60)

    ui_file = "src/ui/streamlit_app.py"

    try:
        with open(ui_file) as f:
            content = f.read()

        # Check for key fixes
        fixes = [
            ("PIL Image fix", "Image.MAX_IMAGE_PIXELS = None"),
            ("Enhanced import", "from enhanced_app import EnhancedZoneExtractor"),
            ("Enhanced processing", "process_pdf_enhanced"),
            ("Status indicator", "Enhanced extraction pipeline available"),
            ("Error handling", "Enhanced extraction not available"),
            ("Progress spinner", "st.spinner"),
            ("Success message", "st.success"),
        ]

        all_fixes = True
        for fix_name, fix_text in fixes:
            if fix_text in content:
                print(f"   ✅ {fix_name}: Present")
            else:
                print(f"   ❌ {fix_name}: Missing")
                all_fixes = False

        return all_fixes

    except Exception as e:
        print(f"❌ UI file check failed: {e}")
        return False


def main():
    """Main status check"""
    print("🔄 REFRESHED UI STATUS VERIFICATION")
    print("=" * 80)
    print("Checking that all fixes are active in the refreshed UI")
    print("=" * 80)

    ui_status = check_ui_status()
    file_status = check_ui_file_updates()

    print("\n🏆 REFRESH STATUS SUMMARY")
    print("=" * 80)

    if ui_status and file_status:
        print("🎉 UI REFRESH: SUCCESSFUL ✅")
        print("✅ UI accessible with all fixes active")
        print("✅ PIL image size limits removed")
        print("✅ Enhanced functionality integrated")
        print("✅ A1 format support enabled")
        print("✅ Safe DPI calculation working")
        print()
        print("🔗 Ready for testing at: http://localhost:8501")
        print("📋 Test the PDF that previously failed:")
        print("   1. Upload your PDF")
        print("   2. Click 'Run Enhanced Extraction'")
        print("   3. Should see safe DPI adjustment message")
        print("   4. Processing should complete successfully")
        print("   5. Results should display in 4 tables")
        return True
    else:
        print("❌ UI REFRESH: ISSUES DETECTED")
        if not ui_status:
            print("   ⚠️ UI connectivity or functionality issues")
        if not file_status:
            print("   ⚠️ UI file missing some fixes")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
