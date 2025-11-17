"""
Image alignment functionality for OCR processing.

This module handles aligning multiple images based on text overlaps,
using bounding box detection to find Y-coordinate offsets between consecutive images.
"""

from difflib import SequenceMatcher
from boundboxes import Boundboxes


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