#!/usr/bin/env python3
"""
MULTI-AGENT DEBUGGING TEST
Critical Issue: 0 codes associated to zones despite detection
"""

from enhanced_app import EnhancedZoneExtractor
import json

def debug_association_pipeline():
    """Debug the complete association pipeline"""
    print("🔬 MULTI-AGENT DEBUG: Association Pipeline Analysis")
    print("=" * 60)
    
    # Create extractor
    extractor = EnhancedZoneExtractor()
    
    # Process with full debugging
    print("📄 Processing: architectural_test.pdf")
    results = extractor.process_pdf_enhanced('architectural_test.pdf')
    
    print("\n📊 RESULTS ANALYSIS:")
    print(f"   Zones: {len(results['zones'])}")
    print(f"   Codes: {len(results['codes'])}")
    print(f"   OCR Data: {len(results.get('ocr_data', []))}")
    
    print("\n🔍 ZONE DETAILS:")
    for i, zone in enumerate(results['zones']):
        print(f"   Zone {i}: '{zone.get('zone_area', zone.get('text', 'UNKNOWN'))}'")
        # Check if zone has polygon
        if 'shapely_polygon' in zone:
            print(f"      Shapely Polygon: ✅")
        else:
            print(f"      Shapely Polygon: ❌")
    
    print("\n🔍 CODE DETAILS:")
    for i, code in enumerate(results['codes']):
        print(f"   Code {i}: '{code.get('code', code.get('text', 'UNKNOWN'))}'")
        print(f"      Type: {code.get('type', 'UNKNOWN')}")
        print(f"      Confidence: {code.get('confidence', 'UNKNOWN')}")
    
    print("\n🔍 OCR DATA CHECK:")
    ocr_data = results.get('ocr_data', [])
    print(f"   OCR words available: {len(ocr_data)}")
    if ocr_data:
        print("   Sample OCR entries:")
        for word in ocr_data[:5]:  # First 5 words
            print(f"      '{word.get('text', '')}' @ ({word.get('x', 0)}, {word.get('y', 0)})")
    
    print("\n🏗️ MEMORY MANAGER ANALYSIS:")
    registry = extractor.memory_manager.zone_registry
    print(f"   Zones in registry: {len(registry)}")
    
    for zone_id, zone_data in registry.items():
        codes_count = len(zone_data['furniture_codes'])
        print(f"   {zone_id}: {codes_count} codes associated")
        if zone_data['furniture_codes']:
            for code in zone_data['furniture_codes']:
                print(f"      └─ {code['code']}")
    
    print("\n🔧 ASSOCIATION TEST:")
    # Test association logic directly
    print("   Testing association logic manually...")
    
    # Get a sample code and zone
    if results['codes'] and results['zones']:
        sample_code = results['codes'][0]
        sample_zone = results['zones'][0]
        
        print(f"   Sample Code: {sample_code}")
        print(f"   Sample Zone: {sample_zone}")
        
        # Test if we can find positions
        code_text = sample_code.get('code', sample_code.get('text', ''))
        zone_text = sample_zone.get('zone_area', sample_zone.get('text', ''))
        
        print(f"   Looking for code '{code_text}' in OCR data...")
        print(f"   Looking for zone '{zone_text}' in OCR data...")
        
        code_found = False
        zone_found = False
        
        for word in ocr_data:
            word_text = word.get('text', '').strip().upper()
            if code_text.upper() in word_text:
                print(f"      Code found: '{word_text}' @ ({word.get('x')}, {word.get('y')})")
                code_found = True
            if any(zone_part.upper() in word_text for zone_part in zone_text.split()):
                print(f"      Zone word found: '{word_text}' @ ({word.get('x')}, {word.get('y')})")
                zone_found = True
        
        print(f"   Code position found: {code_found}")
        print(f"   Zone position found: {zone_found}")
    
    print(f"\n🎯 FINAL VALIDATION:")
    validation = extractor.memory_manager.validate_completeness()
    print(f"   {json.dumps(validation, indent=2, default=str)}")
    
    print(f"\n🚨 DIAGNOSIS:")
    if validation['zones_with_codes'] == 0:
        print("   ❌ CRITICAL: No codes associated with any zones")
        print("   💡 Possible causes:")
        print("      1. Association function not being called")
        print("      2. OCR position data not available")
        print("      3. Code/zone text mismatch")
        print("      4. Distance threshold too strict")
        print("      5. Zone polygon creation failed")
    else:
        print("   ✅ SUCCESS: Codes are being associated properly")

if __name__ == "__main__":
    debug_association_pipeline()