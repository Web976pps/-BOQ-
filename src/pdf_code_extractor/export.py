"""CSV export functionality for A1 PDF zones & codes extraction."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from loguru import logger


def write_csvs(data_rows: List[Dict[str, Any]], output_dir: Path) -> None:
    """
    Write CSV files from extracted zone/code data.
    
    Creates multiple CSV output files:
    - row_level_instances.csv: Individual detections with full details
    - unique_zone_codes.csv: Unique zone-code combinations
    - zone_prefix_summary.csv: Count by zone and prefix
    - global_prefix_summary.csv: Overall prefix counts
    
    Args:
        data_rows: List of dictionaries containing extracted data
        output_dir: Directory to write CSV files to
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not data_rows:
        logger.warning("No data provided for CSV export")
        _write_empty_csvs(output_dir)
        return
    
    logger.info(f"Writing CSV files for {len(data_rows)} data rows to {output_dir}")
    
    # 1. Row-level instances (raw data)
    row_level_file = output_dir / "row_level_instances.csv"
    _write_row_level_csv(data_rows, row_level_file)
    
    # 2. Unique zone-code combinations
    unique_file = output_dir / "unique_zone_codes.csv"
    _write_unique_combinations_csv(data_rows, unique_file)
    
    # 3. Zone x Prefix summary
    zone_prefix_file = output_dir / "zone_prefix_summary.csv"
    _write_zone_prefix_summary_csv(data_rows, zone_prefix_file)
    
    # 4. Global prefix summary
    global_prefix_file = output_dir / "global_prefix_summary.csv"
    _write_global_prefix_summary_csv(data_rows, global_prefix_file)
    
    logger.info("CSV export completed successfully")


def _write_empty_csvs(output_dir: Path) -> None:
    """Write empty CSV files with proper headers when no data is available."""
    
    # Row level instances
    with open(output_dir / "row_level_instances.csv", 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['page', 'zone', 'code', 'prefix', 'conf', 'distance_px', 'strategy_used'])
    
    # Unique zone codes
    with open(output_dir / "unique_zone_codes.csv", 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['zone', 'code', 'prefix', 'conf'])
    
    # Zone prefix summary
    with open(output_dir / "zone_prefix_summary.csv", 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['zone', 'prefix', 'count'])
    
    # Global prefix summary
    with open(output_dir / "global_prefix_summary.csv", 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['prefix', 'count'])


def _write_row_level_csv(data_rows: List[Dict[str, Any]], file_path: Path) -> None:
    """Write row-level instances CSV with individual detections."""
    
    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow(['page', 'zone', 'code', 'prefix', 'conf', 'distance_px', 'strategy_used'])
        
        # Data rows
        for row in data_rows:
            writer.writerow([
                row.get('page', 1),
                row.get('zone_name', ''),
                row.get('code', ''),
                row.get('prefix', ''),
                row.get('confidence', 0.0),
                row.get('distance', 0),
                row.get('method', 'unknown')
            ])
    
    logger.info(f"Written {len(data_rows)} rows to {file_path}")


def _write_unique_combinations_csv(data_rows: List[Dict[str, Any]], file_path: Path) -> None:
    """Write unique zone-code combinations CSV."""
    
    # Create unique combinations
    unique_combinations = set()
    for row in data_rows:
        zone = row.get('zone_name', '')
        code = row.get('code', '')
        prefix = row.get('prefix', '')
        conf = row.get('confidence', 0.0)
        
        if zone and code:
            unique_combinations.add((zone, code, prefix, conf))
    
    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow(['zone', 'code', 'prefix', 'conf'])
        
        # Sort combinations for consistent output
        for zone, code, prefix, conf in sorted(unique_combinations):
            writer.writerow([zone, code, prefix, conf])
    
    logger.info(f"Written {len(unique_combinations)} unique combinations to {file_path}")


def _write_zone_prefix_summary_csv(data_rows: List[Dict[str, Any]], file_path: Path) -> None:
    """Write zone x prefix summary CSV with counts."""
    
    # Count by zone and prefix
    zone_prefix_counts = {}
    for row in data_rows:
        zone = row.get('zone_name', '')
        prefix = row.get('prefix', '')
        
        if zone and prefix:
            key = (zone, prefix)
            zone_prefix_counts[key] = zone_prefix_counts.get(key, 0) + 1
    
    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow(['zone', 'prefix', 'count'])
        
        # Sort by zone then prefix
        for (zone, prefix), count in sorted(zone_prefix_counts.items()):
            writer.writerow([zone, prefix, count])
    
    logger.info(f"Written {len(zone_prefix_counts)} zone-prefix combinations to {file_path}")


def _write_global_prefix_summary_csv(data_rows: List[Dict[str, Any]], file_path: Path) -> None:
    """Write global prefix summary CSV with total counts."""
    
    # Count by prefix globally
    prefix_counts = {}
    for row in data_rows:
        prefix = row.get('prefix', '')
        if prefix:
            prefix_counts[prefix] = prefix_counts.get(prefix, 0) + 1
    
    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow(['prefix', 'count'])
        
        # Sort by prefix
        for prefix in sorted(prefix_counts.keys()):
            writer.writerow([prefix, prefix_counts[prefix]])
    
    logger.info(f"Written {len(prefix_counts)} prefix totals to {file_path}")


def write_overlays(
    data_rows: List[Dict[str, Any]], 
    zones: List[Dict[str, Any]], 
    page_images: Dict[int, Path], 
    output_dir: Path
) -> None:
    """
    Write visual overlay images showing detected zones and codes.
    
    Args:
        data_rows: Extracted zone/code data with coordinates
        zones: Zone detection data
        page_images: Mapping of page numbers to image file paths
        output_dir: Directory to write overlay images to
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not page_images:
        logger.warning("No page images provided for overlay generation")
        return
    
    logger.info(f"Generating overlays for {len(page_images)} pages")
    
    try:
        import cv2
        import numpy as np
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as e:
        logger.error(f"Missing dependencies for overlay generation: {e}")
        logger.info("Install opencv-python and Pillow to enable overlay generation")
        return
    
    for page_num, image_path in page_images.items():
        try:
            _create_page_overlay(
                page_num, image_path, data_rows, zones, output_dir
            )
        except Exception as e:
            logger.error(f"Failed to create overlay for page {page_num}: {e}")
    
    logger.info("Overlay generation completed")


def _create_page_overlay(
    page_num: int,
    image_path: Path,
    data_rows: List[Dict[str, Any]],
    zones: List[Dict[str, Any]],
    output_dir: Path
) -> None:
    """Create an overlay image for a single page."""
    
    from PIL import Image, ImageDraw, ImageFont
    
    # Load base image
    image = Image.open(image_path)
    draw = ImageDraw.Draw(image)
    
    # Try to load a font, fall back to default if not available
    try:
        font = ImageFont.truetype("arial.ttf", 24)
        small_font = ImageFont.truetype("arial.ttf", 16)
    except (OSError, IOError):
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    # Draw zones
    for zone in zones:
        if zone.get('page') == page_num:
            x = zone.get('x', 0)
            y = zone.get('y', 0)
            zone_name = zone.get('zone_area', zone.get('zone_code', ''))
            
            # Draw zone marker (green circle)
            draw.ellipse([x-10, y-10, x+10, y+10], fill='green', outline='darkgreen')
            # Draw zone label
            draw.text((x+15, y-10), zone_name, fill='green', font=font)
    
    # Draw codes
    for row in data_rows:
        if row.get('page') == page_num:
            x = row.get('x', 0)
            y = row.get('y', 0)
            code = row.get('code', '')
            prefix = row.get('prefix', '')
            
            if code:
                # Color by prefix
                color = _get_prefix_color(prefix)
                
                # Draw code marker (colored square)
                draw.rectangle([x-8, y-8, x+8, y+8], fill=color, outline='black')
                # Draw code label
                draw.text((x+12, y-8), code, fill=color, font=small_font)
    
    # Save overlay image
    overlay_filename = f"page_{page_num}_overlay.png"
    overlay_path = output_dir / overlay_filename
    image.save(overlay_path)
    
    logger.debug(f"Created overlay: {overlay_path}")


def _get_prefix_color(prefix: str) -> str:
    """Get color for furniture code prefix."""
    color_map = {
        'CH': 'blue',      # Chairs
        'TB': 'red',       # Tables  
        'C': 'orange',     # Counters/Cabinets
        'SU': 'purple',    # Storage Units
        'KT': 'brown',     # Kitchen
    }
    return color_map.get(prefix, 'gray')


def export_summary_json(
    data_rows: List[Dict[str, Any]], 
    zones: List[Dict[str, Any]], 
    output_dir: Path
) -> None:
    """Export a JSON summary of the extraction results."""
    
    summary = {
        'extraction_summary': {
            'total_data_rows': len(data_rows),
            'total_zones': len(zones),
            'zones_by_page': _count_by_page(zones),
            'codes_by_prefix': _count_by_prefix(data_rows),
            'extraction_stats': _calculate_stats(data_rows, zones)
        },
        'zones': zones,
        'codes': data_rows
    }
    
    summary_file = output_dir / "extraction_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Summary JSON written to {summary_file}")


def _count_by_page(items: List[Dict[str, Any]]) -> Dict[int, int]:
    """Count items by page number."""
    counts = {}
    for item in items:
        page = item.get('page', 1)
        counts[page] = counts.get(page, 0) + 1
    return counts


def _count_by_prefix(data_rows: List[Dict[str, Any]]) -> Dict[str, int]:
    """Count codes by prefix."""
    counts = {}
    for row in data_rows:
        prefix = row.get('prefix', '')
        if prefix:
            counts[prefix] = counts.get(prefix, 0) + 1
    return counts


def _calculate_stats(data_rows: List[Dict[str, Any]], zones: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate extraction statistics."""
    
    # Confidence statistics
    confidences = [row.get('confidence', 0.0) for row in data_rows if row.get('confidence')]
    zone_confidences = [zone.get('confidence', 0.0) for zone in zones if zone.get('confidence')]
    
    return {
        'avg_code_confidence': sum(confidences) / len(confidences) if confidences else 0.0,
        'avg_zone_confidence': sum(zone_confidences) / len(zone_confidences) if zone_confidences else 0.0,
        'min_confidence': min(confidences + zone_confidences) if (confidences or zone_confidences) else 0.0,
        'max_confidence': max(confidences + zone_confidences) if (confidences or zone_confidences) else 0.0,
        'unique_prefixes': len(set(row.get('prefix', '') for row in data_rows if row.get('prefix'))),
        'unique_zones': len(set(zone.get('zone_area', '') for zone in zones if zone.get('zone_area')))
    }