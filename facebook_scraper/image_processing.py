"""
Generic image processing functionality for OCR workflows.

This module handles generic image operations like aligning multiple images,
combining them into a single visualization, and drawing bounding boxes.
These functions are reusable across different document processing tasks.
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from .boundboxes import Boundboxes
from .image_alignment import find_alignment_offsets_boundboxes


def align_and_combine_images(ocr_boundboxes_list, folder_path, annotated_dir):
    """
    Align Boundboxes and create combined image visualization.
    """
    print("🔄 Aligning images using text overlaps...")

    # Find alignment offsets
    offsets, match_positions = find_alignment_offsets_boundboxes(ocr_boundboxes_list)

    # Apply offsets to create aligned boundboxes
    all_aligned_boxes = []

    # First image has no offset
    all_aligned_boxes.extend(ocr_boundboxes_list[0].boxes)

    # Apply offsets to remaining images
    running_offset = 0.0
    for boundboxes, offset in zip(ocr_boundboxes_list[1:], offsets):
        running_offset += offset
        aligned_boundboxes = boundboxes.apply_offset(running_offset)
        all_aligned_boxes.extend(aligned_boundboxes.boxes)

    # Create combined image (simplified version - just stacking)
    image_files = sorted(folder_path.glob("*.png"), key=lambda x: int(x.stem))

    if not image_files:
        print("❌ No images found for combination")
        return Boundboxes(all_aligned_boxes)

    # Load first image to get dimensions
    img = Image.open(image_files[0])
    running_offset = 0
    for image_file, offset, match_pos in zip(image_files[1:], offsets, match_positions):
        crop = img.crop((0, 0, img.width, int(running_offset + match_pos)))
        new_img = Image.open(image_file)
        running_offset += offset
        new_height = running_offset + new_img.height
        combined_img = Image.new('RGB', (img.width, int(new_height)), 'white')
        combined_img.paste(crop, (0, 0))
        insert_height = new_height - new_img.height + match_pos - offset
        combined_img.paste(new_img.crop((0, int(match_pos - offset), new_img.width, new_img.height)), (0, int(insert_height)))
        img = combined_img

    # Save combined image
    combined_path = annotated_dir / "combined.png"
    img.save(combined_path)
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