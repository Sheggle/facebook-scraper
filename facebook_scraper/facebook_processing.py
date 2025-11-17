"""
Facebook-specific processing functionality for OCR workflows.

This module handles Facebook-specific operations like detecting comment regions
based on Facebook UI elements ('beantwoorden' buttons, 'meest relevant' text, etc.).
These functions contain domain-specific logic for Facebook's interface.
"""

import statistics
from pathlib import Path
from PIL import Image, ImageDraw
from .boundboxes import Boundboxes
from .content_parser import parse_comment


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