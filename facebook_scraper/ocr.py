#!/usr/bin/env python3
"""
OCR script to process screenshots from scraper.py output - REFACTORED VERSION.
"""

import argparse
import json
from pathlib import Path
from .boundboxes import Boundboxes
from .easy_ocr import EasyOCR
from .image_processing import align_and_combine_images, draw_bounding_boxes_on_combined
from .facebook_processing import shade_comment_regions
from .content_parser import parse_post

POST_BOUNDARY_X1 = 280
POST_BOUNDARY_X2 = 1020
POST_BOUNDARY_Y1 = 90
POST_BOUNDARY_Y2 = 580


def main():
    parser = argparse.ArgumentParser(description='OCR processor for Facebook screenshots - REFACTORED VERSION')
    parser.add_argument('folder', help='Folder containing ordered images (0.png, 1.png, etc.)')
    args = parser.parse_args()

    folder_path = Path(args.folder)

    if not folder_path.exists():
        print(f"❌ Folder not found: {folder_path}")
        return

    # Initialize EasyOCR wrapper with content filtering
    ocr_reader = EasyOCR(
        languages=['en', 'nl'],
        content_filter=True,
        filter_x1=POST_BOUNDARY_X1,
        filter_x2=POST_BOUNDARY_X2,
        filter_y1=POST_BOUNDARY_Y1,
        filter_y2=POST_BOUNDARY_Y2
    )

    # Get all PNG files and sort them numerically
    image_files = sorted(folder_path.glob("*.png"), key=lambda x: int(x.stem))

    if not image_files:
        print(f"❌ No PNG files found in {folder_path}")
        return

    print(f"📸 Found {len(image_files)} images to process")

    # Create annotated output folder
    annotated_dir = Path("annotated") / folder_path.name
    annotated_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 Output folder: {annotated_dir}")

    # Process each image using EasyOCR wrapper
    ocr_boundboxes_list = []

    for image_file in image_files:
        print(f"\n📄 Processing: {image_file.name}")

        # Process image with EasyOCR wrapper (returns Boundboxes directly)
        boundboxes = ocr_reader(str(image_file))
        ocr_boundboxes_list.append(boundboxes)

        print(f"✅ Extracted {len(boundboxes.boxes)} content-area detections")

    # Align images and create combined image
    aligned_boundboxes = align_and_combine_images(ocr_boundboxes_list, folder_path, annotated_dir)

    # Deduplicate overlapping bounding boxes
    deduplicated_boundboxes = aligned_boundboxes.remove_duplicates()

    # Draw deduplicated bounding boxes on combined image
    draw_bounding_boxes_on_combined(deduplicated_boundboxes, annotated_dir)

    # Create comment region visualization and get parsed comments
    comment_regions = shade_comment_regions(deduplicated_boundboxes, annotated_dir)

    # Parse the main post content
    print("\n" + "="*60)
    print("📰 PARSING POST CONTENT")
    print("="*60)
    post_data = parse_post(deduplicated_boundboxes)

    # Collect parsed comments
    comments = []
    if comment_regions:
        for region in comment_regions:
            if "parsed" in region:
                comments.append(region["parsed"])

    # Create structured data
    structured_data = {
        "post": post_data,
        "comments": comments
    }

    # Save structured JSON
    structured_json_file = annotated_dir / "parsed_data.json"
    with open(structured_json_file, 'w', encoding='utf-8') as f:
        json.dump(structured_data, f, indent=2, ensure_ascii=False)

    print(f"💾 Structured data saved to: {structured_json_file}")

    # Save aligned and deduplicated OCR results as JSON (for debugging)
    debug_data = []
    for box in deduplicated_boundboxes.boxes:
        debug_data.append({
            "bbox": {
                "x1": float(box.x1),
                "x2": float(box.x2),
                "y1": float(box.y1),
                "y2": float(box.y2)
            },
            "text": box.text,
            "confidence": float(box.confidence)
        })

    json_file = annotated_dir / "ocr_results.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(debug_data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Finished processing {len(image_files)} images")
    print(f"📊 Final stats: {len(deduplicated_boundboxes.boxes)} deduplicated detections")
    print(f"📝 Parsed: 1 post, {len(comments)} comments")


if __name__ == "__main__":
    main()