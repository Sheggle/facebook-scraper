"""
Content parsing functionality for OCR processing.

This module handles parsing structured data from OCR results,
extracting meaningful information like usernames, dates, and text content
from Facebook post and comment data.
"""

from .boundboxes import Boundboxes


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

    # Remove 'Volgen' from author name
    author = author.replace('Volgen', '').strip()

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