#!/usr/bin/env python3
"""
Test Fixed UI Functionality
Tests the updated UI with enhanced functionality instead of broken pipeline
"""

import requests
import time
import os
import sys
import tempfile

# Add project root to path
sys.path.insert(0, '/workspace')


def test_fixed_ui_functionality():
    """Test the fixed UI functionality"""
    print("🔧 TESTING FIXED UI FUNCTIONALITY")
    print("=" * 60)
    
    # Test UI connectivity
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
    
    # Test enhanced functionality import
    try:
        from enhanced_app import EnhancedZoneExtractor
        extractor = EnhancedZoneExtractor()
        print("✅ Enhanced functionality available in UI")
    except ImportError as e:
        print(f"❌ Enhanced functionality not available: {e}")
        return False
    
    # Test processing with the same functionality the UI would use
    test_file = "architectural_test.pdf"
    if os.path.exists(test_file):
        print(f"✅ Test file available: {test_file}")
        
        try:
            # Simulate the same processing the UI would do
            with open(test_file, 'rb') as f:
                pdf_content = f.read()
            
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_file.write(pdf_content)
                temp_file.flush()
                
                start_time = time.time()
                results = extractor.process_pdf_enhanced(temp_file.name)
                processing_time = time.time() - start_time
                
                os.unlink(temp_file.name)
            
            if results:
                zones = results.get('zones', [])
                codes = results.get('codes', [])
                
                print(f"✅ Processing successful")
                print(f"   📊 Results: {len(zones)} zones, {len(codes)} codes")
                print(f"   ⏱️ Time: {processing_time:.2f}s")
                
                # Test data formatting that UI would do
                row_level_data = []
                for i, zone in enumerate(zones):
                    row_level_data.append({
                        'Type': 'Zone',
                        'Text': zone.get('text', f'Zone_{i+1}'),
                        'Confidence': zone.get('confidence', 0)
                    })
                
                for i, code in enumerate(codes):
                    row_level_data.append({
                        'Type': 'Code', 
                        'Text': code.get('text', f'Code_{i+1}'),
                        'Confidence': code.get('confidence', 0)
                    })
                
                print(f"✅ Data formatting successful: {len(row_level_data)} total entries")
                return True
            else:
                print("❌ Processing failed: No results")
                return False
                
        except Exception as e:
            print(f"❌ Processing test failed: {e}")
            return False
    else:
        print(f"❌ Test file not found: {test_file}")
        return False


def test_ui_component_structure():
    """Test that the UI file has the right structure"""
    print("\n📱 TESTING UI COMPONENT STRUCTURE")
    print("=" * 60)
    
    ui_file = "src/ui/streamlit_app.py"
    
    try:
        with open(ui_file, 'r') as f:
            ui_content = f.read()
        
        # Check for new enhanced components
        enhanced_components = [
            "EnhancedZoneExtractor",
            "process_pdf_enhanced", 
            "st.spinner",
            "st.success",
            "st.metric",
            "Enhanced extraction pipeline available"
        ]
        
        found_components = []
        for component in enhanced_components:
            if component in ui_content:
                found_components.append(component)
                print(f"   ✅ Found: {component}")
            else:
                print(f"   ❌ Missing: {component}")
        
        # Check that old broken components are removed
        removed_components = [
            "subprocess.run",
            "src.extract_zones_codes"
        ]
        
        properly_removed = []
        for component in removed_components:
            if component not in ui_content:
                properly_removed.append(component)
                print(f"   ✅ Removed: {component}")
            else:
                print(f"   ⚠️ Still present: {component}")
        
        component_score = len(found_components) / len(enhanced_components) * 100
        removal_score = len(properly_removed) / len(removed_components) * 100
        
        print(f"\n📊 Enhanced Components: {component_score:.1f}% ({len(found_components)}/{len(enhanced_components)})")
        print(f"📊 Removed Broken Components: {removal_score:.1f}% ({len(properly_removed)}/{len(removed_components)})")
        
        return component_score >= 80 and removal_score >= 80
        
    except Exception as e:
        print(f"❌ UI structure test failed: {e}")
        return False


def main():
    """Main test execution"""
    print("🔧 TESTING FIXED UI AFTER PIPELINE ERROR FIX")
    print("=" * 80)
    print("Testing updated UI that uses enhanced functionality instead of broken pipeline")
    print("=" * 80)
    
    # Wait for UI to be ready
    print("⏳ Waiting for updated UI to be ready...")
    time.sleep(3)
    
    # Run tests
    functionality_test = test_fixed_ui_functionality()
    structure_test = test_ui_component_structure()
    
    # Summary
    print("\n🏆 FIXED UI TEST SUMMARY")
    print("=" * 80)
    
    tests_passed = sum([functionality_test, structure_test])
    total_tests = 2
    
    print(f"✅ Tests Passed: {tests_passed}/{total_tests}")
    print(f"📊 Success Rate: {(tests_passed/total_tests)*100:.1f}%")
    
    if tests_passed == total_tests:
        print("🎉 FIXED UI: ALL TESTS PASSED")
        print("✅ UI now uses working enhanced functionality")
        print("✅ Broken pipeline components removed")
        print("✅ Same interface with enhanced backend")
        print()
        print("🔗 Updated UI accessible at: http://localhost:8501")
        print("📋 Ready for manual testing:")
        print("   1. Upload a PDF")
        print("   2. Click 'Run Enhanced Extraction'")
        print("   3. Verify 4 result tables display")
        print("   4. Test CSV download buttons")
        return True
    else:
        print("❌ FIXED UI: SOME TESTS FAILED")
        print("⚠️ Additional fixes may be needed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)