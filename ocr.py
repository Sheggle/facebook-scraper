#!/usr/bin/env python3
"""
OCR script to process screenshots from scraper.py output.
"""

import argparse
import easyocr
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from difflib import SequenceMatcher

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


def apply_offset(image_data, y_offset):
    """
    Apply Y-coordinate offset to all detections in an image.
    Creates a new image_data dict with adjusted coordinates.
    """
    adjusted_image = {
        "filename": image_data["filename"],
        "detections": []
    }

    # Add error field if it exists
    if "error" in image_data:
        adjusted_image["error"] = image_data["error"]

    for detection in image_data["detections"]:
        adjusted_detection = detection.copy()

        # Adjust bbox coordinates
        adjusted_detection["bbox"] = {
            "x1": detection["bbox"]["x1"],
            "x2": detection["bbox"]["x2"],
            "y1": detection["bbox"]["y1"] + y_offset,
            "y2": detection["bbox"]["y2"] + y_offset
        }

        # Adjust bbox_points coordinates
        adjusted_detection["bbox_points"] = [
            [point[0], point[1] + y_offset] for point in detection["bbox_points"]
        ]

        adjusted_image["detections"].append(adjusted_detection)

    return adjusted_image


def find_y_offset(prev_image, curr_image):
    """
    Find Y-coordinate offset between consecutive images using text overlaps.
    Only considers unique texts within each image for reliable alignment.
    Returns tuple (offset, merge_y1) if overlaps are found, (None, None) if no valid overlaps exist.
    merge_y1 is the Y1 coordinate where images should be merged.
    """
    prev_detections = prev_image["detections"]
    curr_detections = curr_image["detections"]

    if not prev_detections or not curr_detections:
        return None, None

    # Filter to only unique texts within each image
    prev_unique = {}  # text -> detection
    for det in prev_detections:
        text = det["text"]
        if text not in prev_unique:
            prev_unique[text] = det
        else:
            # Remove duplicates by setting to None
            prev_unique[text] = None

    curr_unique = {}  # text -> detection
    for det in curr_detections:
        text = det["text"]
        if text not in curr_unique:
            curr_unique[text] = det
        else:
            # Remove duplicates by setting to None
            curr_unique[text] = None

    # Filter out None values (duplicates)
    prev_unique = {k: v for k, v in prev_unique.items() if v is not None}
    curr_unique = {k: v for k, v in curr_unique.items() if v is not None}

    used_prev_texts = set()

    for curr_text, curr_det in curr_unique.items():
        best_match = None
        best_score = 0

        for prev_text, prev_det in prev_unique.items():
            if prev_text in used_prev_texts:
                continue

            # Check text similarity (require 0.9 minimum)
            score = text_similarity(curr_text, prev_text)
            if score < 0.9:
                continue

            # Check x1 coordinate proximity (within 10 pixels)
            x1_diff = abs(curr_det["bbox"]["x1"] - prev_det["bbox"]["x1"])
            if x1_diff > 10:
                continue

            if score > best_score:
                best_match = (prev_text, prev_det)
                best_score = score

        if best_match:
            prev_text, prev_det = best_match
            used_prev_texts.add(prev_text)

            # Calculate y_mid for both detections
            curr_y_mid = (curr_det["bbox"]["y1"] + curr_det["bbox"]["y2"]) / 2
            prev_y_mid = (prev_det["bbox"]["y1"] + prev_det["bbox"]["y2"]) / 2

            # Return the offset and merge point Y1 coordinate
            offset = prev_y_mid - curr_y_mid
            merge_y1 = prev_det["bbox"]["y1"]  # Use Y1 of overlapping box as merge point
            return offset, merge_y1

    # No valid overlaps found
    return None, None


def align_images_to_base(ocr_results, folder_path, annotated_dir):
    """
    Align all images to the coordinate system of image 0 using text overlap detection.
    Also creates a combined image showing the complete scrolled content.

    Args:
        ocr_results: List of image OCR results from individual processing
        folder_path: Path to original images folder
        annotated_dir: Path to output directory for combined image

    Returns:
        List of aligned image results where all coordinates are relative to image 0

    Raises:
        ValueError: If no overlaps found between any consecutive images
    """
    if len(ocr_results) < 2:
        return ocr_results

    print("\n🔄 Starting image alignment and combination...")

    # Load all images for combining
    image_files = []
    for result in ocr_results:
        image_path = folder_path / result["filename"]
        img = Image.open(image_path)
        image_files.append(img)

    # Initialize with first image
    combined_img = image_files[0].copy()

    aligned_results = [ocr_results[0]]  # Image 0 is the base - keep unchanged
    cumulative_offset = 0

    for i in range(1, len(ocr_results)):
        prev_image = ocr_results[i-1]  # Previous image in original coordinate system
        curr_image = ocr_results[i]    # Current image to align

        print(f"  🔍 Aligning image {i} with image {i-1}...")

        # Find Y-offset and merge point between consecutive images
        result = find_y_offset(prev_image, curr_image)
        print(result)

        if result[0] is None:
            print(f"No overlaps found between image {i-1} and {i}. Alignment failed.")
            break

        offset, merge_y1 = result

        # Update cumulative offset (relative to base image 0)
        cumulative_offset += offset

        print(f"    📐 Offset: {offset:.2f}px, Merge at Y1: {merge_y1:.2f}px, Cumulative: {cumulative_offset:.2f}px")

        # Apply cumulative offset to align with base coordinate system
        adjusted_image = apply_offset(curr_image, cumulative_offset)
        aligned_results.append(adjusted_image)

        # Combine images using merge point
        curr_img = image_files[i]

        new_canvas = Image.new('RGB', (combined_img.width, int(cumulative_offset + curr_img.height)), 'white')

        print(cumulative_offset - offset + merge_y1)

        # Paste existing combined image at top
        cropped_combined = combined_img.crop((0, 0, combined_img.width, int(cumulative_offset - offset + merge_y1)))
        new_canvas.paste(cropped_combined, (0, 0))

        # Crop and paste current image below merge point
        cropped_curr = curr_img.crop((0, int(merge_y1 - offset), curr_img.width, curr_img.height))
        print(cropped_curr.height, cropped_curr.width)
        print(cropped_combined.height, cropped_combined.width)
        print(new_canvas.height, new_canvas.width)
        new_canvas.paste(cropped_curr, (0, cropped_combined.height))

        # Draw boundary line
        draw = ImageDraw.Draw(new_canvas)
        draw.line([(0, cropped_combined.height), (new_canvas.width, cropped_combined.height)], fill='red', width=2)

        combined_img = new_canvas

    # Save combined image
    combined_path = annotated_dir / "combined.png"
    combined_img.save(combined_path)
    print(f"🖼️  Combined image saved: {combined_path}")

    # Flatten all detections since they're now in unified coordinate system
    all_detections = []
    for image_result in aligned_results:
        all_detections.extend(image_result["detections"])

    print(f"✅ Successfully aligned {len(aligned_results)} images to unified coordinate system")
    print(f"📦 Total detections in unified system: {len(all_detections)}")
    return all_detections


def draw_bounding_boxes_on_combined(deduplicated_detections, annotated_dir):
    """
    Draw deduplicated bounding boxes on the combined image.

    Args:
        deduplicated_detections: Flat list of deduplicated detections
        annotated_dir: Path to output directory
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

    # Draw bounding boxes for all deduplicated detections
    for detection in deduplicated_detections:
        bbox = detection["bbox"]
        text = detection["text"]

        # Draw red bounding box
        draw.rectangle([bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]],
                      outline="red", width=2)

        # Draw text above the bounding box
        text_y = max(0, bbox["y1"] - 20)  # Position above box, but not off screen
        draw.text((bbox["x1"], text_y), text, fill="red", font=font)

    # Save annotated combined image
    annotated_combined_path = annotated_dir / "combined_with_boxes.png"
    combined_img.save(annotated_combined_path)
    print(f"📦 Combined image with {len(deduplicated_detections)} deduplicated bounding boxes saved: {annotated_combined_path}")


def deduplicate_bboxes(all_detections):
    """
    Remove smaller bounding boxes that are covered by more than 50% by larger ones.
    Uses efficient Y-overlap filtering to avoid unnecessary comparisons.

    Args:
        all_detections: Flat list of detections with unified coordinates

    Returns:
        Flat list of deduplicated detections
    """
    print("🔄 Deduplicating overlapping bounding boxes...")
    print(f"📦 Total detections before deduplication: {len(all_detections)}")

    # Sort by y1 for efficient Y-overlap checking
    all_detections.sort(key=lambda x: x["bbox"]["y1"])

    # Track which detections to keep
    keep_indices = set(range(len(all_detections)))

    for i in range(len(all_detections)):
        if i not in keep_indices:
            continue

        det1 = all_detections[i]
        bbox1 = det1["bbox"]
        area1 = (bbox1["x2"] - bbox1["x1"]) * (bbox1["y2"] - bbox1["y1"])

        # Only check detections that could overlap in Y dimension
        for j in range(i + 1, len(all_detections)):
            if j not in keep_indices:
                continue

            det2 = all_detections[j]
            bbox2 = det2["bbox"]

            # Early termination: if det2.y1 >= det1.y2, no more overlaps possible
            if bbox2["y1"] >= bbox1["y2"]:
                break

            # Check Y-overlap condition: det2.y1 < det1.y2 and det2.y2 > det1.y1
            if bbox2["y2"] <= bbox1["y1"]:
                continue

            area2 = (bbox2["x2"] - bbox2["x1"]) * (bbox2["y2"] - bbox2["y1"])

            # Calculate intersection
            x_overlap = max(0, min(bbox1["x2"], bbox2["x2"]) - max(bbox1["x1"], bbox2["x1"]))
            y_overlap = max(0, min(bbox1["y2"], bbox2["y2"]) - max(bbox1["y1"], bbox2["y1"]))
            intersection = x_overlap * y_overlap

            # Check if smaller box is covered by more than 50%
            if area1 < area2:
                coverage = intersection / area1 if area1 > 0 else 0
                if coverage > 0.5:
                    keep_indices.discard(i)
                    break
            else:
                coverage = intersection / area2 if area2 > 0 else 0
                if coverage > 0.5:
                    keep_indices.discard(j)

    # Return only the kept detections as a flat list
    deduplicated_detections = [all_detections[i] for i in keep_indices]
    print(f"📦 Detections after deduplication: {len(deduplicated_detections)}")

    return deduplicated_detections


def shade_comment_regions(all_detections, annotated_dir):
    """
    Find comment regions using 'beantwoorden' buttons and 'meest relevant' boundary,
    then create a shaded visualization showing comment boundaries.

    Args:
        all_detections: Flat list of detections with unified coordinates
        annotated_dir: Path to output directory
    """
    print("🔍 Finding comment regions...")

    # Step 1: Find all 'beantwoorden' buttons
    beantwoorden_buttons = []
    for detection in all_detections:
        if "beantwoorden" in detection["text"].lower():
            beantwoorden_buttons.append(detection)

    if not beantwoorden_buttons:
        print("❌ No 'beantwoorden' buttons found")
        return

    print(f"📍 Found {len(beantwoorden_buttons)} 'beantwoorden' buttons")

    # Calculate median height (y2 - y1) and x1 coordinates
    heights = [det["bbox"]["y2"] - det["bbox"]["y1"] for det in beantwoorden_buttons]
    x1_coords = [det["bbox"]["x1"] for det in beantwoorden_buttons]

    import statistics
    median_height = statistics.median(heights)
    median_x1 = statistics.median(x1_coords)

    print(f"📐 Median height: {median_height:.1f}px, median x1: {median_x1:.1f}px")

    # Filter buttons within thresholds
    filtered_buttons = []
    for detection in beantwoorden_buttons:
        height = detection["bbox"]["y2"] - detection["bbox"]["y1"]
        x1 = detection["bbox"]["x1"]

        if abs(height - median_height) <= 5 and abs(x1 - median_x1) <= 50:
            filtered_buttons.append(detection)

    print(f"✅ Filtered to {len(filtered_buttons)} 'beantwoorden' buttons within thresholds")

    # Step 2: Find 'meest relevant' starting point
    meest_relevant = None
    for detection in all_detections:
        if "meest relevant" in detection["text"].lower():
            meest_relevant = detection
            break

    if not meest_relevant:
        print("❌ No 'meest relevant' text found")
        return

    start_y = meest_relevant["bbox"]["y2"]
    print(f"📍 Found 'meest relevant' starting at Y: {start_y:.1f}px")

    # Step 3: Define comment regions
    # Sort filtered buttons by Y-coordinate
    filtered_buttons.sort(key=lambda det: det["bbox"]["y2"])

    comment_regions = []
    current_y = start_y

    for button in filtered_buttons:
        end_y = button["bbox"]["y2"]
        if end_y > current_y:  # Only add regions that have positive height
            comment_regions.append({
                "start_y": current_y,
                "end_y": end_y,
                "button": button
            })
            current_y = end_y

    print(f"📝 Created {len(comment_regions)} comment regions")

    # Step 4: Create shaded visualization
    combined_path = annotated_dir / "combined.png"
    if not combined_path.exists():
        print("❌ combined.png not found")
        return

    # Load combined image
    combined_img = Image.open(combined_path)
    draw = ImageDraw.Draw(combined_img)

    # Draw colored borders around each comment region
    border_color = "blue"
    border_width = 3

    for i, region in enumerate(comment_regions):
        # Draw rectangle border for the comment region
        # Use full width of the image
        x1 = POST_BOUNDARY_X1
        x2 = POST_BOUNDARY_X2
        y1 = int(region["start_y"])
        y2 = int(region["end_y"])

        # Draw border
        draw.rectangle([x1, y1, x2, y2], outline=border_color, width=border_width)

        print(f"   Region {i+1}: Y {y1} -> {y2} (height: {y2-y1}px)")

    # Save shaded image
    shaded_path = annotated_dir / "combined_shaded.png"
    combined_img.save(shaded_path)
    print(f"🎨 Comment regions shaded and saved: {shaded_path}")

    return comment_regions


def main():
    parser = argparse.ArgumentParser(description='OCR processor for Facebook screenshots')
    parser.add_argument('folder', help='Folder containing ordered images (0.png, 1.png, etc.)')
    args = parser.parse_args()

    folder_path = Path(args.folder)

    if not folder_path.exists():
        print(f"❌ Folder not found: {folder_path}")
        return

    # Initialize EasyOCR reader for Dutch and English
    print("🔍 Initializing EasyOCR (Dutch + English)...")
    reader = easyocr.Reader(['en', 'nl'])

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

    # Store all OCR results for JSON export
    ocr_results = []

    # Process each image in order
    for image_file in image_files:
        print(f"\n" + "="*60)
        print(f"📄 Processing: {image_file.name}")
        print("="*60)

        # Run OCR on the image
        result = reader.readtext(str(image_file))

        # Filter to only include content area (main Facebook content column)
        filtered_result = []
        for bbox, text, confidence in result:
            # Extract bounding box coordinates
            x_coords = [point[0] for point in bbox]
            y_coords = [point[1] for point in bbox]
            x1, x2 = min(x_coords), max(x_coords)
            y1, y2 = min(y_coords), max(y_coords)

            # Check if bounding box is entirely within content area
            if (x1 >= POST_BOUNDARY_X1 and x2 <= POST_BOUNDARY_X2 and y1 >= POST_BOUNDARY_Y1 and y2 <= POST_BOUNDARY_Y2):
                filtered_result.append((bbox, text, confidence))

        # Use filtered result for all further processing
        result = filtered_result
        print(f"  📍 Filtered to {len(result)} detections in content area")

        # Prepare data for JSON export
        image_data = {
            "filename": image_file.name,
            "detections": []
        }

        # Load image for annotation
        img = Image.open(image_file)
        draw = ImageDraw.Draw(img)

        font = ImageFont.truetype("Arial.ttf", 16)

        # Print detected text and draw annotations
        if result:
            for i, (bbox, text, confidence) in enumerate(result):
                print(f"  [{i+1}] {text} (confidence: {confidence:.2f})")

                # Extract bounding box coordinates
                # bbox is [(x1,y1), (x2,y2), (x3,y3), (x4,y4)]
                x_coords = [point[0] for point in bbox]
                y_coords = [point[1] for point in bbox]
                x1, x2 = min(x_coords), max(x_coords)
                y1, y2 = min(y_coords), max(y_coords)

                # Store detection data for JSON (convert numpy types to Python types)
                detection = {
                    "text": text,
                    "confidence": float(confidence),
                    "bbox": {
                        "x1": float(x1), "y1": float(y1), "x2": float(x2), "y2": float(y2)
                    },
                    "bbox_points": [[float(point[0]), float(point[1])] for point in bbox]
                }
                image_data["detections"].append(detection)

                # Draw red bounding box
                draw.rectangle([x1, y1, x2, y2], outline="red", width=2)

                # Draw text above the bounding box
                text_y = max(0, y1 - 20)  # Position above box, but not off screen
                draw.text((x1, text_y), text, fill="red", font=font)

            # Save annotated image
            output_file = annotated_dir / image_file.name
            img.save(output_file)
            print(f"  💾 Saved annotated image: {output_file}")

        else:
            print("  No text detected")
            # Still save the image (without annotations)
            output_file = annotated_dir / image_file.name
            img.save(output_file)

        # Add image data to results
        ocr_results.append(image_data)

    # Align all images to unified coordinate system
    all_detections = align_images_to_base(ocr_results, folder_path, annotated_dir)

    # Deduplicate overlapping bounding boxes
    deduplicated_detections = deduplicate_bboxes(all_detections)

    # Draw deduplicated bounding boxes on combined image
    draw_bounding_boxes_on_combined(deduplicated_detections, annotated_dir)

    # Create comment region visualization
    shade_comment_regions(deduplicated_detections, annotated_dir)

    # Save aligned and deduplicated OCR results as JSON
    json_file = annotated_dir / "ocr_results.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(deduplicated_detections, f, indent=2, ensure_ascii=False)

    # combine images

    print(f"\n✅ Finished processing {len(image_files)} images")
    print(f"📄 OCR results saved to: {json_file}")


if __name__ == "__main__":
    main()