#!/usr/bin/env python3
"""
CLI wrapper for Enhanced A1 PDF Zones/Codes Extractor
Provides command-line interface for the enhanced functionality
"""

import argparse
import sys
import os
from pathlib import Path
import tempfile
import time

# Import enhanced functionality
from enhanced_app import EnhancedZoneExtractor, A1PDFProcessor, GeometricAnalyzer, ZoneMemoryManager


def create_cli_parser():
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description="Enhanced A1 PDF Zones/Codes Extractor - CLI Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --pdf architectural_test.pdf --output results/
  %(prog)s --pdf input/sample.pdf --output outputs/ --dpi 300
  %(prog)s --pdf test.pdf --output results/ --verbose
        """
    )
    
    parser.add_argument(
        "--pdf", 
        required=True,
        help="Path to input PDF file"
    )
    
    parser.add_argument(
        "--output", "-o",
        default="outputs/cli_results",
        help="Output directory for results (default: outputs/cli_results)"
    )
    
    parser.add_argument(
        "--dpi",
        type=int,
        default=600,
        help="DPI for PDF rasterization (default: 600)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.5,
        help="Minimum confidence threshold for detections (default: 0.5)"
    )
    
    return parser


def setup_output_directory(output_path):
    """Create output directory if it doesn't exist"""
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def process_pdf_cli(pdf_path, output_dir, dpi=600, verbose=False, confidence_threshold=0.5):
    """Process PDF using enhanced extraction pipeline"""
    
    if verbose:
        print(f"🚀 Enhanced A1 PDF Zones/Codes Extractor CLI")
        print(f"=" * 60)
        print(f"📄 Input PDF: {pdf_path}")
        print(f"📁 Output Directory: {output_dir}")
        print(f"🔍 DPI: {dpi}")
        print(f"🎯 Confidence Threshold: {confidence_threshold}")
        print()
    
    # Verify PDF exists
    if not os.path.exists(pdf_path):
        print(f"❌ Error: PDF file not found: {pdf_path}")
        return False
    
    # Get file size
    file_size = os.path.getsize(pdf_path)
    if verbose:
        print(f"📊 File size: {file_size:,} bytes")
    
    try:
        # Initialize enhanced extractor
        if verbose:
            print(f"🔧 Initializing Enhanced Zone Extractor...")
        
        extractor = EnhancedZoneExtractor()
        # Update DPI in the PDF processor
        extractor.pdf_processor.target_dpi = dpi
        
        if verbose:
            print(f"   ✅ PDF Processor ready (DPI: {dpi})")
            print(f"   ✅ Geometric Analyzer ready")
            print(f"   ✅ Memory Manager ready")
            print()
        
        # Process PDF
        start_time = time.time()
        
        if verbose:
            print(f"🔍 Processing PDF with enhanced detection...")
        
        # Use temporary file to simulate upload behavior
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            # Copy PDF to temp file
            with open(pdf_path, 'rb') as src:
                temp_file.write(src.read())
            temp_file.flush()
            
            # Process using enhanced extractor
            results = extractor.process_pdf_enhanced(temp_file.name)
            
            # Clean up temp file
            os.unlink(temp_file.name)
        
        processing_time = time.time() - start_time
        
        if verbose:
            print(f"   ⏱️ Processing completed in {processing_time:.2f} seconds")
            print()
        
        # Display results
        if verbose:
            print(f"📊 Detection Results:")
            print(f"   🏢 Zones detected: {len(results.get('zones', []))}")
            print(f"   🪑 Codes detected: {len(results.get('codes', []))}")
            
            # Show detected zones
            zones = results.get('zones', [])
            if zones:
                print(f"\n🏢 Detected Zones:")
                for i, zone in enumerate(zones, 1):
                    zone_text = zone.get('text', 'Unknown')
                    confidence = zone.get('confidence', 0)
                    print(f"   {i}. {zone_text} (confidence: {confidence:.2f})")
            
            # Show detected codes
            codes = results.get('codes', [])
            if codes:
                print(f"\n🪑 Detected Codes:")
                for i, code in enumerate(codes, 1):
                    code_text = code.get('text', 'Unknown')
                    code_type = code.get('type', 'Unknown')
                    confidence = code.get('confidence', 0)
                    print(f"   {i}. {code_text} ({code_type}, confidence: {confidence:.2f})")
            
            print()
        
        # Save results to CSV
        csv_filename = output_dir / f"enhanced_extraction_results_{int(time.time())}.csv"
        
        if verbose:
            print(f"💾 Saving results to CSV: {csv_filename}")
        
        # Create CSV data
        import pandas as pd
        
        csv_data = []
        
        # Add zones
        for zone in results.get('zones', []):
            csv_data.append({
                'Type': 'Zone',
                'Text': zone.get('zone_area', ''),  # Fixed: use 'zone_area' instead of 'text'
                'Category': 'Zone/Area',
                'Confidence': zone.get('confidence', 0),
                'Coordinates': f"({zone.get('x', 0)}, {zone.get('y', 0)})"  # Fixed: use actual coordinate fields
            })
        
        # Add codes
        for code in results.get('codes', []):
            csv_data.append({
                'Type': 'Code',
                'Text': code.get('code', ''),  # Fixed: use 'code' instead of 'text'
                'Category': code.get('code_type', ''),  # Fixed: use 'code_type' instead of 'type'
                'Confidence': code.get('confidence', 0),
                'Coordinates': f"({code.get('x', 0)}, {code.get('y', 0)})"  # Fixed: use actual coordinate fields
            })
        
        # Save CSV
        if csv_data:
            df = pd.DataFrame(csv_data)
            df.to_csv(csv_filename, index=False, encoding='utf-8')
            
            if verbose:
                print(f"   ✅ CSV saved with {len(csv_data)} entries")
        else:
            if verbose:
                print(f"   ⚠️ No data to save")
        
        # Save processing summary
        summary_filename = output_dir / f"processing_summary_{int(time.time())}.txt"
        
        with open(summary_filename, 'w', encoding='utf-8') as f:
            f.write(f"Enhanced A1 PDF Zones/Codes Extractor - Processing Summary\n")
            f.write(f"=" * 60 + "\n\n")
            f.write(f"Input PDF: {pdf_path}\n")
            f.write(f"File Size: {file_size:,} bytes\n")
            f.write(f"Processing Time: {processing_time:.2f} seconds\n")
            f.write(f"DPI: {dpi}\n")
            f.write(f"Confidence Threshold: {confidence_threshold}\n\n")
            f.write(f"Results:\n")
            f.write(f"  Zones detected: {len(results.get('zones', []))}\n")
            f.write(f"  Codes detected: {len(results.get('codes', []))}\n\n")
            
            if results.get('validation'):
                f.write(f"Validation Summary:\n")
                validation = results['validation']
                f.write(f"  Total zones: {validation.get('total_zones', 0)}\n")
                f.write(f"  Zones with codes: {validation.get('zones_with_codes', 0)}\n")
                f.write(f"  Average confidence: {validation.get('avg_confidence', 0):.2f}\n")
                f.write(f"  Issues: {len(validation.get('issues', []))}\n")
        
        if verbose:
            print(f"   ✅ Summary saved to: {summary_filename}")
            print()
        
        print(f"✅ Processing completed successfully!")
        print(f"📁 Results saved to: {output_dir}")
        print(f"📊 Zones: {len(results.get('zones', []))}, Codes: {len(results.get('codes', []))}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during processing: {str(e)}")
        if verbose:
            import traceback
            traceback.print_exc()
        return False


def main():
    """Main CLI entry point"""
    parser = create_cli_parser()
    args = parser.parse_args()
    
    # Setup output directory
    output_dir = setup_output_directory(args.output)
    
    # Process PDF
    success = process_pdf_cli(
        pdf_path=args.pdf,
        output_dir=output_dir,
        dpi=args.dpi,
        verbose=args.verbose,
        confidence_threshold=args.confidence_threshold
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()