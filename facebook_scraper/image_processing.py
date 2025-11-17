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