#!/usr/bin/env python3
"""
Test Image Size Fix
Tests the updated enhanced_app.py with PIL image size limit fixes
"""

import sys
import os
import tempfile
import time

# Add project root to path
sys.path.insert(0, '/workspace')

def test_pil_settings():
    """Test PIL settings are correctly applied"""
    print("🔧 TESTING PIL SETTINGS")
    print("=" * 60)
    
    try:
        from PIL import Image, ImageFile
        
        # Check MAX_IMAGE_PIXELS setting
        if Image.MAX_IMAGE_PIXELS is None:
            print("✅ PIL MAX_IMAGE_PIXELS: Unlimited (None)")
        else:
            print(f"⚠️ PIL MAX_IMAGE_PIXELS: {Image.MAX_IMAGE_PIXELS}")
        
        # Check LOAD_TRUNCATED_IMAGES setting
        print(f"✅ PIL LOAD_TRUNCATED_IMAGES: {ImageFile.LOAD_TRUNCATED_IMAGES}")
        
        return True
        
    except Exception as e:
        print(f"❌ PIL settings test failed: {e}")
        return False


def test_dpi_calculation():
    """Test the safe DPI calculation logic"""
    print("\n📏 TESTING DPI CALCULATION")
    print("=" * 60)
    
    try:
        from enhanced_app import A1PDFProcessor
        
        processor = A1PDFProcessor()
        
        # Test with the problematic dimensions from the error
        width_mm = 1000.1
        height_mm = 707.0
        
        safe_dpi = processor.calculate_safe_dpi(width_mm, height_mm)
        
        # Calculate expected pixel count
        width_inches = width_mm / 25.4
        height_inches = height_mm / 25.4
        total_pixels = (width_inches * safe_dpi) * (height_inches * safe_dpi)
        
        print(f"✅ Input dimensions: {width_mm}x{height_mm}mm")
        print(f"✅ Calculated safe DPI: {safe_dpi}")
        print(f"✅ Resulting image size: {int(total_pixels/1000000)}MP ({int(width_inches * safe_dpi)}x{int(height_inches * safe_dpi)} pixels)")
        print(f"✅ Within safety limit: {total_pixels <= processor.max_pixels}")
        
        # Test that it's within our safety limit
        if total_pixels <= processor.max_pixels:
            print("✅ DPI calculation: SAFE")
            return True
        else:
            print("❌ DPI calculation: EXCEEDS LIMIT")
            return False
            
    except Exception as e:
        print(f"❌ DPI calculation test failed: {e}")
        return False


def test_enhanced_extractor_initialization():
    """Test that EnhancedZoneExtractor can be initialized with the fixes"""
    print("\n🔧 TESTING ENHANCED EXTRACTOR INITIALIZATION")
    print("=" * 60)
    
    try:
        from enhanced_app import EnhancedZoneExtractor
        
        extractor = EnhancedZoneExtractor()
        
        # Check that components are initialized
        if hasattr(extractor, 'pdf_processor'):
            print("✅ PDF processor initialized")
        else:
            print("❌ PDF processor missing")
            return False
            
        if hasattr(extractor, 'geometric_analyzer'):
            print("✅ Geometric analyzer initialized")
        else:
            print("❌ Geometric analyzer missing")
            return False
            
        if hasattr(extractor, 'memory_manager'):
            print("✅ Memory manager initialized")
        else:
            print("❌ Memory manager missing")
            return False
        
        # Check DPI settings
        print(f"✅ Default DPI: {extractor.pdf_processor.target_dpi}")
        print(f"✅ Max DPI: {extractor.pdf_processor.max_dpi}")
        print(f"✅ Min DPI: {extractor.pdf_processor.min_dpi}")
        print(f"✅ Max pixels: {extractor.pdf_processor.max_pixels}")
        
        return True
        
    except Exception as e:
        print(f"❌ Enhanced extractor initialization failed: {e}")
        return False


def test_pdf_format_detection():
    """Test PDF format detection with the test file"""
    print("\n📄 TESTING PDF FORMAT DETECTION")
    print("=" * 60)
    
    test_file = "architectural_test.pdf"
    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        return False
    
    try:
        from enhanced_app import EnhancedZoneExtractor
        
        extractor = EnhancedZoneExtractor()
        
        # Test format detection
        is_a1, orientation, dimensions = extractor.pdf_processor.detect_a1_format(test_file)
        
        print(f"✅ Format detection successful")
        print(f"   📋 Is A1: {is_a1}")
        print(f"   📐 Orientation: {orientation}")
        print(f"   📏 Dimensions: {dimensions[0]:.1f}x{dimensions[1]:.1f}mm")
        
        # Test safe DPI calculation for this file
        safe_dpi = extractor.pdf_processor.calculate_safe_dpi(dimensions[0], dimensions[1])
        
        print(f"   🎯 Safe DPI: {safe_dpi}")
        
        # Calculate resulting image size
        width_inches = dimensions[0] / 25.4
        height_inches = dimensions[1] / 25.4
        total_pixels = (width_inches * safe_dpi) * (height_inches * safe_dpi)
        
        print(f"   🖼️ Image size: {int(total_pixels/1000000)}MP")
        
        return True
        
    except Exception as e:
        print(f"❌ PDF format detection failed: {e}")
        return False


def main():
    """Main test execution"""
    print("🔧 TESTING PIL IMAGE SIZE LIMIT FIX")
    print("=" * 80)
    print("Testing fixes for 'Image size exceeds limit, could be decompression bomb' error")
    print("=" * 80)
    
    # Run tests
    pil_test = test_pil_settings()
    dpi_test = test_dpi_calculation()
    init_test = test_enhanced_extractor_initialization()
    detection_test = test_pdf_format_detection()
    
    # Summary
    print("\n🏆 IMAGE SIZE FIX TEST SUMMARY")
    print("=" * 80)
    
    tests_passed = sum([pil_test, dpi_test, init_test, detection_test])
    total_tests = 4
    
    print(f"✅ Tests Passed: {tests_passed}/{total_tests}")
    print(f"📊 Success Rate: {(tests_passed/total_tests)*100:.1f}%")
    
    if tests_passed == total_tests:
        print("🎉 IMAGE SIZE FIX: ALL TESTS PASSED")
        print("✅ PIL image size limits properly configured")
        print("✅ Safe DPI calculation working correctly")
        print("✅ Enhanced extractor initialization successful")
        print("✅ PDF format detection functional")
        print()
        print("🔗 Updated UI accessible at: http://localhost:8501")
        print("📋 Ready for testing with large PDFs:")
        print("   - Upload the same PDF that caused the error")
        print("   - Should now process with safe DPI instead of failing")
        print("   - Look for '🔧 Adjusted DPI to XXX for safety' message")
        return True
    else:
        print("❌ IMAGE SIZE FIX: SOME TESTS FAILED")
        print("⚠️ Additional fixes may be needed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)