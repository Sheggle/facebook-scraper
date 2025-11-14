#!/usr/bin/env python3
"""
OCR script to process screenshots from scraper.py output - REFACTORED VERSION.
"""

import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from difflib import SequenceMatcher
from boundboxes import Boundboxes
from easy_ocr import EasyOCR

POST_BOUNDARY_X1 = 280
POST_BOUNDARY_X2 = 1020
POST_BOUNDARY_Y1 = 90
POST_BOUNDARY_Y2 = 580


def text_similarity(text1, text2):
    """
    Calculate normalized similarity score (0-1, higher is better) using SequenceMatcher.
    Returns 1.0 for identical strings, approaching 0.0 for completely different strings.
    """
    matcher = SequenceMatcher(None, text1, text2)
    return matcher.ratio()


def find_alignment_offsets_boundboxes(boundboxes_list):
    """
    Find Y-coordinate offsets between consecutive Boundboxes using text overlaps.
    Returns list of cumulative offsets to align all to base (first) image.
    """
    if len(boundboxes_list) <= 1:
        return [0.0]

    cumulative_offsets = [0.0]  # First image is the base

    for i in range(1, len(boundboxes_list)):
        prev_boxes = boundboxes_list[i-1]
        curr_boxes = boundboxes_list[i]

        # Find overlapping text between consecutive images
        offset = find_y_offset_boundboxes(prev_boxes, curr_boxes)

        if offset is not None:
            cumulative_offsets.append(cumulative_offsets[-1] + offset)
            print(f"   Image {i}: offset = {offset:.1f}px (cumulative: {cumulative_offsets[-1]:.1f}px)")
        else:
            print(f"   Image {i}: No alignment found, using previous offset")
            cumulative_offsets.append(cumulative_offsets[-1])

    return cumulative_offsets


def find_y_offset_boundboxes(prev_boundboxes: Boundboxes, curr_boundboxes: Boundboxes):
    """
    Find Y-coordinate offset between consecutive Boundboxes using text overlaps.
    Only considers unique texts within each image for reliable alignment.
    Returns offset if overlaps are found, None if no valid overlaps exist.
    """
    if not prev_boundboxes.boxes or not curr_boundboxes.boxes:
        return None

    # Filter to only unique texts within each image
    prev_unique = {}
    for box in prev_boundboxes.boxes:
        text = box.text
        if text not in prev_unique:
            prev_unique[text] = box
        else:
            prev_unique[text] = None  # Mark as duplicate

    curr_unique = {}
    for box in curr_boundboxes.boxes:
        text = box.text
        if text not in curr_unique:
            curr_unique[text] = box
        else:
            curr_unique[text] = None  # Mark as duplicate

    # Filter out duplicates
    prev_unique = {k: v for k, v in prev_unique.items() if v is not None}
    curr_unique = {k: v for k, v in curr_unique.items() if v is not None}

    used_prev_texts = set()

    for curr_text, curr_box in curr_unique.items():
        best_match = None
        best_score = 0

        for prev_text, prev_box in prev_unique.items():
            if prev_text in used_prev_texts:
                continue

            # Check text similarity (require 0.9 minimum)
            score = text_similarity(curr_text, prev_text)
            if score < 0.9:
                continue

            # Check x1 coordinate proximity (within 10 pixels)
            x1_diff = abs(curr_box.x1 - prev_box.x1)
            if x1_diff > 10:
                continue

            if score > best_score:
                best_match = (prev_text, prev_box)
                best_score = score

        if best_match:
            prev_text, prev_box = best_match
            used_prev_texts.add(prev_text)

            # Calculate y_mid for both detections
            curr_y_mid = (curr_box.y1 + curr_box.y2) / 2
            prev_y_mid = (prev_box.y1 + prev_box.y2) / 2

            # Return the offset
            offset = prev_y_mid - curr_y_mid
            return offset

    # No valid overlaps found
    return None


def align_and_combine_images(ocr_boundboxes_list, folder_path, annotated_dir):
    """
    Align Boundboxes and create combined image visualization.
    """
    print("🔄 Aligning images using text overlaps...")

    # Find alignment offsets
    offsets = find_alignment_offsets_boundboxes(ocr_boundboxes_list)

    # Apply offsets to create aligned boundboxes
    all_aligned_boxes = []

    for i, (boundboxes, offset) in enumerate(zip(ocr_boundboxes_list, offsets)):
        if offset != 0:
            aligned_boundboxes = boundboxes.apply_offset(offset)
        else:
            aligned_boundboxes = boundboxes
        all_aligned_boxes.extend(aligned_boundboxes.boxes)

    # Create combined image (simplified version - just stacking)
    image_files = sorted(folder_path.glob("*.png"), key=lambda x: int(x.stem))

    if not image_files:
        print("❌ No images found for combination")
        return Boundboxes(all_aligned_boxes)

    # Load first image to get dimensions
    first_img = Image.open(image_files[0])
    combined_height = len(image_files) * first_img.height
    combined_img = Image.new('RGB', (first_img.width, combined_height), 'white')

    # Simple stacking for now - would need proper alignment for production
    for i, img_file in enumerate(image_files):
        img = Image.open(img_file)
        y_pos = i * img.height
        combined_img.paste(img, (0, y_pos))

    # Save combined image
    combined_path = annotated_dir / "combined.png"
    combined_img.save(combined_path)
    print(f"🖼️  Combined image saved: {combined_path}")

    return Boundboxes(all_aligned_boxes)


def draw_bounding_boxes_on_combined(boundboxes: Boundboxes, annotated_dir):
    """
    Draw Boundboxes on the combined image.
    """
    print("🎯 Drawing deduplicated bounding boxes on combined image...")

    combined_path = annotated_dir / "combined.png"
    if not combined_path.exists():
        print("❌ combined.png not found")
        return

    # Load combined image
    combined_img = Image.open(combined_path)
    draw = ImageDraw.Draw(combined_img)
    font = ImageFont.truetype("Arial.ttf", 16)

    # Draw bounding boxes for all boxes
    for box in boundboxes.boxes:
        # Draw red bounding box
        draw.rectangle([box.x1, box.y1, box.x2, box.y2], outline="red", width=2)

        # Draw text above the bounding box
        text_y = max(0, box.y1 - 20)  # Position above box, but not off screen
        draw.text((box.x1, text_y), box.text, fill="red", font=font)

    # Save annotated combined image
    annotated_combined_path = annotated_dir / "combined_with_boxes.png"
    combined_img.save(annotated_combined_path)
    print(f"📦 Combined image with {len(boundboxes.boxes)} deduplicated bounding boxes saved: {annotated_combined_path}")


def shade_comment_regions(boundboxes: Boundboxes, annotated_dir):
    """
    Find comment regions using 'beantwoorden' buttons and create visualization using Boundboxes.
    """
    print("🔍 Finding comment regions...")

    # Step 1: Find all 'beantwoorden' buttons
    beantwoorden_boxes = [box for box in boundboxes.boxes if "beantwoorden" in box.text.lower()]

    if not beantwoorden_boxes:
        print("❌ No 'beantwoorden' buttons found")
        return []

    print(f"📍 Found {len(beantwoorden_boxes)} 'beantwoorden' buttons")

    # Calculate median height and x1 coordinates
    import statistics
    heights = [box.height for box in beantwoorden_boxes]
    x1_coords = [box.x1 for box in beantwoorden_boxes]

    median_height = statistics.median(heights)
    median_x1 = statistics.median(x1_coords)

    print(f"📐 Median height: {median_height:.1f}px, median x1: {median_x1:.1f}px")

    # Filter buttons within thresholds
    filtered_buttons = []
    for box in beantwoorden_boxes:
        if abs(box.height - median_height) <= 5 and abs(box.x1 - median_x1) <= 50:
            filtered_buttons.append(box)

    print(f"✅ Filtered to {len(filtered_buttons)} 'beantwoorden' buttons within thresholds")

    # Step 2: Find 'meest relevant' starting point
    meest_relevant = None
    for box in boundboxes.boxes:
        if "meest relevant" in box.text.lower():
            meest_relevant = box
            break

    if not meest_relevant:
        print("❌ No 'meest relevant' text found")
        return []

    start_y = meest_relevant.y2
    print(f"📍 Found 'meest relevant' starting at Y: {start_y:.1f}px")

    # Step 3: Define comment regions and parse each
    filtered_buttons.sort(key=lambda box: box.y2)
    comment_regions = []
    current_y = start_y

    for button in filtered_buttons:
        end_y = button.y2
        if end_y > current_y:
            region = {
                "start_y": current_y,
                "end_y": end_y,
                "button": button
            }

            # Get boxes in this region
            region_boundboxes = boundboxes.find_boxes_in_region(current_y, end_y)

            # Check for 'antwoord' boxes and adjust top if needed
            if region_boundboxes.boxes:
                top_line = region_boundboxes.pop_top_line()
                antwoord_boxes = [box for box in top_line.boxes if 'antwoord' in box.text.lower()]

                if antwoord_boxes:
                    antwoord_y2 = antwoord_boxes[0].y2
                    region["start_y"] = antwoord_y2
                    print(f"   📝 Adjusted region top from {current_y:.1f} to {antwoord_y2:.1f} due to 'antwoord' box")
                    # Update region boxes with new boundary
                    region_boundboxes = boundboxes.find_boxes_in_region(antwoord_y2, end_y)

            # Parse comment from this region
            if region_boundboxes.boxes:
                comment_data = parse_comment(region_boundboxes)
                print(comment_data)
                region["parsed"] = comment_data

            comment_regions.append(region)
            current_y = end_y

    print(f"📝 Created {len(comment_regions)} comment regions")

    # Step 4: Create shaded visualization
    combined_path = annotated_dir / "combined.png"
    if not combined_path.exists():
        print("❌ combined.png not found")
        return comment_regions

    combined_img = Image.open(combined_path)
    draw = ImageDraw.Draw(combined_img)
    border_color = "blue"
    border_width = 3

    for i, region in enumerate(comment_regions):
        x1 = 0
        x2 = combined_img.width
        y1 = int(region["start_y"])
        y2 = int(region["end_y"])

        draw.rectangle([x1, y1, x2, y2], outline=border_color, width=border_width)
        print(f"   Region {i+1}: Y {y1} -> {y2} (height: {y2-y1}px)")

    shaded_path = annotated_dir / "combined_shaded.png"
    combined_img.save(shaded_path)
    print(f"🎨 Comment regions shaded and saved: {shaded_path}")

    return comment_regions


def parse_comment(region_boundboxes: Boundboxes):
    """
    Parse a comment region to extract username, date, and text using Boundboxes.
    """
    if not region_boundboxes.boxes:
        return {"username": "", "date": "", "text": ""}

    # Extract username from top line
    top_line = region_boundboxes.pop_top_line()
    username = top_line.to_text_line()

    # Extract date from bottom line (filtering UI elements)
    bottom_line = region_boundboxes.pop_bottom_line()
    date_line = bottom_line.remove_matching(['leuk', 'beantwoorden', 'bewerkt'])
    date = date_line.to_text_line()

    # Extract main comment text from remaining boxes
    middle_boxes = region_boundboxes.exclude_top_and_bottom_lines()
    text = middle_boxes.create_readable_text()

    return {"username": username, "date": date, "text": text}


def parse_post(boundboxes: Boundboxes):
    """
    Parse the main post content by finding the comments boundary and extracting author, date, and text.
    """
    # Find comments boundary using regex pattern
    comments_box = boundboxes.find_pattern(r'^\d+ opmerkingen$')

    if not comments_box:
        print("❌ No comments pattern found")
        return {"author": "", "date": "", "text": ""}

    print(f"📍 Found comments pattern at Y: {comments_box.y1:.1f}px")

    # Get post boxes above the comments boundary
    post_boundboxes = boundboxes.find_boxes_above(comments_box.y1, margin=10)
    print(f"📦 Found {len(post_boundboxes.boxes)} post boxes")

    if not post_boundboxes.boxes:
        return {"author": "", "date": "", "text": ""}

    # Extract author from first line
    first_line = post_boundboxes.pop_top_line()
    author = first_line.to_text_line()

    # Extract date from second line (remaining boxes after removing first line)
    remaining_boxes = [box for box in post_boundboxes.boxes if box not in first_line.boxes]
    if remaining_boxes:
        remaining_boundboxes = Boundboxes(remaining_boxes)
        second_line = remaining_boundboxes.pop_top_line()
        date = second_line.to_text_line()

        # Get text from remaining boxes (after removing first and second lines)
        text_boxes = [box for box in remaining_boxes if box not in second_line.boxes]
        text_boundboxes = Boundboxes(text_boxes)
        text = text_boundboxes.create_readable_text()
    else:
        date = ""
        text = ""

    print(f"📝 Post author: {author}")
    print(f"📅 Post date: {date}")
    print(f"📄 Post text: {text}")

    return {"author": author, "date": date, "text": text}


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