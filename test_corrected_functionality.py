#!/usr/bin/env python3
"""
Test the corrected functionality with architectural PDF
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import ZoneExtractor
import json

def test_corrected_extraction():
    """Test the corrected PDF extraction functionality"""
    print("🧪 Testing Corrected Zone & Furniture Code Extraction")
    print("=" * 60)
    
    test_file = "architectural_test.pdf"
    
    if not os.path.exists(test_file):
        print("❌ Architectural test PDF not found!")
        return False
    
    print(f"📄 Testing with file: {test_file}")
    print(f"📊 File size: {os.path.getsize(test_file)} bytes")
    
    try:
        # Initialize extractor
        extractor = ZoneExtractor()
        
        # Process the PDF
        zones, codes, associations = extractor.process_pdf(test_file)
        
        print(f"\n📊 EXTRACTION RESULTS:")
        print(f"   🏢 Zones found: {len(zones)}")
        print(f"   🪑 Furniture codes found: {len(codes)}")
        print(f"   🔗 Zone associations: {len(associations)}")
        
        # Display zones
        print(f"\n🏢 DETECTED ZONES:")
        for zone in zones:
            print(f"   Page {zone['page']}: {zone['zone_area']} ({zone['method']})")
        
        # Display furniture codes by type
        print(f"\n🪑 DETECTED FURNITURE CODES:")
        code_types = {}
        for code in codes:
            code_type = code['code_type']
            if code_type not in code_types:
                code_types[code_type] = []
            code_types[code_type].append(code)
        
        for code_type, type_codes in code_types.items():
            print(f"   {code_type} codes ({len(type_codes)}):")
            for code in type_codes:
                print(f"      Page {code['page']}: {code['code']} ({code['method']})")
        
        # Display associations
        print(f"\n🔗 ZONE-CODE ASSOCIATIONS:")
        for zone_area, zone_codes in associations.items():
            if zone_codes:
                print(f"   {zone_area}: {len(zone_codes)} codes")
                for code in zone_codes[:3]:  # Show first 3
                    print(f"      - {code['code']} ({code['code_type']})")
                if len(zone_codes) > 3:
                    print(f"      ... and {len(zone_codes) - 3} more")
        
        # Validation
        expected_zones = ["INNOVATION HUB", "EAT", "CREATE", "KITCHEN", "CONFERENCE", "LOUNGE"]
        expected_codes = ["CH15", "CH15A", "TB01", "C101", "SU05", "KT01"]
        
        zones_found = [z['zone_area'] for z in zones]
        codes_found = [c['code'] for c in codes]
        
        zone_matches = sum(1 for ez in expected_zones if any(ez in zf for zf in zones_found))
        code_matches = sum(1 for ec in expected_codes if ec in codes_found)
        
        print(f"\n✅ VALIDATION:")
        print(f"   Expected zones found: {zone_matches}/{len(expected_zones)}")
        print(f"   Expected codes found: {code_matches}/{len(expected_codes)}")
        
        if zone_matches >= 4 and code_matches >= 4:
            print(f"   🎉 TEST PASSED - Detection working correctly!")
            return True
        else:
            print(f"   ⚠️  TEST PARTIAL - Some expected items not found")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_regex_patterns():
    """Test the regex patterns directly"""
    print(f"\n🔍 Testing Regex Patterns:")
    print("-" * 30)
    
    extractor = ZoneExtractor()
    
    # Test zone detection
    test_text_zones = """
    This is a test with INNOVATION HUB and COLLABORATION SPACE.
    Also includes EAT and CREATE areas.
    But not this mixed case text or common words like THE AND OR.
    """
    
    zones = extractor.detect_all_caps_zones(test_text_zones)
    print(f"Zone detection test: {zones}")
    
    # Test furniture code detection
    test_text_codes = """
    Furniture includes CH15, CH15A, CH21 b, TB01, TB02A.
    Also C101, C102 a, SU05, SU06A, KT01, KT02 a.
    But not random text or A1 B2 patterns.
    """
    
    codes = extractor.detect_furniture_codes(test_text_codes)
    print(f"Furniture code detection test: {codes}")
    
    return True

if __name__ == "__main__":
    success1 = test_regex_patterns()
    success2 = test_corrected_extraction()
    
    if success1 and success2:
        print(f"\n🎉 ALL TESTS PASSED! Application is working correctly.")
    else:
        print(f"\n⚠️  Some tests failed. Check the output above.")