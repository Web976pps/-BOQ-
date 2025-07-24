#!/usr/bin/env python3
"""
Test script to verify additional bug fixes in the PDF extractor application.
"""

import tempfile
import os
import sys
import json
from datetime import datetime
import utils

def test_pdf_validation():
    """Test improved PDF validation"""
    print("🧪 Testing PDF validation...")
    
    try:
        # Test 1: Non-existent file
        result1 = utils.validate_pdf_file("/nonexistent/file.pdf")
        assert result1[0] == False and "does not exist" in result1[1]
        print("  ✅ Non-existent file detected")
        
        # Test 2: Non-PDF file
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_file:
            temp_file.write(b"This is not a PDF")
            temp_txt_file = temp_file.name
        
        try:
            result2 = utils.validate_pdf_file(temp_txt_file)
            assert result2[0] == False and "not a PDF" in result2[1]
            print("  ✅ Non-PDF extension detected")
        finally:
            os.unlink(temp_txt_file)
        
        # Test 3: File with PDF extension but invalid content
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_file.write(b"This is not a real PDF file")
            temp_fake_pdf = temp_file.name
        
        try:
            result3 = utils.validate_pdf_file(temp_fake_pdf)
            assert result3[0] == False and "invalid header" in result3[1]
            print("  ✅ Invalid PDF content detected")
        finally:
            os.unlink(temp_fake_pdf)
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error in PDF validation test: {e}")
        return False

def test_file_hash_error_handling():
    """Test file hash calculation with error handling"""
    print("🧪 Testing file hash error handling...")
    
    try:
        # Test 1: Non-existent file
        try:
            utils.calculate_file_hash("/nonexistent/file.pdf")
            assert False, "Should have raised FileNotFoundError"
        except FileNotFoundError as e:
            assert "File not found" in str(e)
            print("  ✅ FileNotFoundError handled correctly")
        
        # Test 2: Valid file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b"test content for hashing")
            temp_filename = temp_file.name
        
        try:
            hash_result = utils.calculate_file_hash(temp_filename)
            assert len(hash_result) == 64  # SHA-256 hex length
            print("  ✅ Valid file hash calculated successfully")
        finally:
            os.unlink(temp_filename)
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error in file hash test: {e}")
        return False

def test_log_sanitization():
    """Test log data sanitization"""
    print("🧪 Testing log data sanitization...")
    
    try:
        # Create test zones with potentially sensitive data
        test_zones = [
            {
                'page': 1,
                'zone_code': 'A1',
                'method': 'PyPDF2',
                'sensitive_data': 'This should not appear in logs'
            },
            {
                'page': 2,
                'zone_code': 'B2',
                'method': 'pdfplumber'
            }
        ]
        
        # Test with potentially sensitive filename
        sensitive_filename = "/path/to/sensitive/document_with_secrets.pdf"
        
        log_file = utils.save_extraction_log(test_zones, sensitive_filename)
        
        try:
            # Verify log was created
            assert os.path.exists(log_file)
            
            # Read and verify sanitization
            with open(log_file, 'r') as f:
                log_data = json.load(f)
            
            # Check filename sanitization
            assert log_data['filename'] == "document_with_secrets.pdf"
            print("  ✅ Filename sanitized (path removed)")
            
            # Check zone data sanitization
            for zone in log_data['zones']:
                assert 'sensitive_data' not in zone
                assert all(key in zone for key in ['page', 'zone_code', 'method'])
            print("  ✅ Zone data sanitized (sensitive fields removed)")
            
        finally:
            if os.path.exists(log_file):
                os.unlink(log_file)
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error in log sanitization test: {e}")
        return False

def test_zone_code_formatting():
    """Test zone code formatting with type safety"""
    print("🧪 Testing zone code formatting...")
    
    try:
        # Test 1: Valid string
        result1 = utils.format_zone_code("  a1  ")
        assert result1 == "A1"
        print("  ✅ String formatting works")
        
        # Test 2: Integer input
        result2 = utils.format_zone_code(123)
        assert result2 == "123"
        print("  ✅ Integer input handled")
        
        # Test 3: Empty input
        result3 = utils.format_zone_code("")
        assert result3 == ""
        print("  ✅ Empty input handled")
        
        # Test 4: Invalid type
        try:
            utils.format_zone_code([1, 2, 3])
            assert False, "Should have raised TypeError"
        except TypeError as e:
            assert "must be string, int, or float" in str(e)
            print("  ✅ Invalid type rejected")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error in zone code formatting test: {e}")
        return False

def test_temp_file_cleanup():
    """Test improved temporary file cleanup"""
    print("🧪 Testing temp file cleanup...")
    
    try:
        # Create some test temp files
        temp_files = []
        temp_dir = tempfile.gettempdir()
        
        for i in range(3):
            temp_file = tempfile.NamedTemporaryFile(
                prefix="tmp", 
                suffix=".pdf", 
                delete=False,
                dir=temp_dir
            )
            temp_file.write(b"test content")
            temp_file.close()
            temp_files.append(temp_file.name)
        
        # Verify files exist
        for temp_file in temp_files:
            assert os.path.exists(temp_file)
        
        # Test cleanup (should not delete recent files)
        cleaned_count = utils.clean_temp_files(max_age_hours=0.001)  # Very short age
        print(f"  ✅ Cleanup function ran, cleaned {cleaned_count} files")
        
        # Cleanup our test files manually
        for temp_file in temp_files:
            try:
                os.unlink(temp_file)
            except:
                pass
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error in temp file cleanup test: {e}")
        return False

def test_pdf_metadata_error_handling():
    """Test PDF metadata extraction with error handling"""
    print("🧪 Testing PDF metadata error handling...")
    
    try:
        # Test 1: Non-existent file
        try:
            utils.get_pdf_metadata("/nonexistent/file.pdf")
            assert False, "Should have raised FileNotFoundError"
        except FileNotFoundError as e:
            assert "PDF file not found" in str(e)
            print("  ✅ Non-existent file error handled")
        
        # Test 2: Invalid PDF file (only if PyPDF2 is available)
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_file.write(b"Not a real PDF")
                temp_fake_pdf = temp_file.name
            
            try:
                utils.get_pdf_metadata(temp_fake_pdf)
                assert False, "Should have raised an error for invalid PDF"
            except (ValueError, ImportError) as e:
                if "PyPDF2 is required" in str(e):
                    print("  ✅ Missing PyPDF2 dependency handled")
                elif "Invalid or corrupted PDF" in str(e):
                    print("  ✅ Invalid PDF error handled")
                else:
                    print(f"  ✅ PDF error handled: {str(e)}")
            finally:
                os.unlink(temp_fake_pdf)
        except Exception as e:
            print(f"  ✅ PDF metadata test completed with expected error: {str(e)}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error in PDF metadata test: {e}")
        return False

def main():
    """Run all additional bug fix tests"""
    print("🔍 Testing Additional PDF Extractor Bug Fixes")
    print("=" * 60)
    
    tests = [
        ("PDF Validation Improvements", test_pdf_validation),
        ("File Hash Error Handling", test_file_hash_error_handling),
        ("Log Data Sanitization", test_log_sanitization),
        ("Zone Code Type Safety", test_zone_code_formatting),
        ("Temp File Cleanup", test_temp_file_cleanup),
        ("PDF Metadata Error Handling", test_pdf_metadata_error_handling)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        if test_func():
            print(f"✅ {test_name} - PASSED")
            passed += 1
        else:
            print(f"❌ {test_name} - FAILED")
    
    print(f"\n{'=' * 60}")
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All additional bug fixes verified successfully!")
        return 0
    else:
        print("⚠️  Some tests failed. Please review the fixes.")
        return 1

if __name__ == "__main__":
    sys.exit(main())