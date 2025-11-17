#!/usr/bin/env python3
"""
EasyOCR wrapper that outputs Boundboxes directly.
"""

import easyocr
from pathlib import Path
from .boundboxes import Boundboxes, Boundbox


class EasyOCR:
    """
    EasyOCR wrapper that processes images and returns Boundboxes with optional content filtering.
    """

    def __init__(self, languages=['en', 'nl'], content_filter=True,
                 filter_x1=280, filter_x2=1020, filter_y1=90, filter_y2=580):
        """
        Initialize EasyOCR reader.

        Args:
            languages: List of language codes for OCR recognition
            content_filter: Whether to apply content area filtering
            filter_x1, filter_x2, filter_y1, filter_y2: Content area boundaries
        """
        print(f"🔍 Initializing EasyOCR ({' + '.join(languages)})...")
        self.reader = easyocr.Reader(languages)
        self.content_filter = content_filter
        self.filter_x1 = filter_x1
        self.filter_x2 = filter_x2
        self.filter_y1 = filter_y1
        self.filter_y2 = filter_y2

    def __call__(self, image_path: str) -> Boundboxes:
        """
        Process an image and return Boundboxes.

        Args:
            image_path: Path to the image file

        Returns:
            Boundboxes instance containing detected text boxes
        """
        image_path = Path(image_path)

        if not image_path.exists():
            print(f"❌ Image not found: {image_path}")
            return Boundboxes([])

        # Run OCR on the image
        result = self.reader.readtext(str(image_path))

        # Convert to Boundboxes
        boxes = []
        for bbox, text, confidence in result:
            # bbox is [(x1,y1), (x2,y2), (x3,y3), (x4,y4)]
            x_coords = [point[0] for point in bbox]
            y_coords = [point[1] for point in bbox]
            x1, x2 = min(x_coords), max(x_coords)
            y1, y2 = min(y_coords), max(y_coords)

            # Apply content area filter if enabled
            if self.content_filter:
                if not (self.filter_x1 <= x1 and x2 <= self.filter_x2 and
                        self.filter_y1 <= y1 and y2 <= self.filter_y2):
                    continue

            box = Boundbox(
                x1=float(x1), y1=float(y1), x2=float(x2), y2=float(y2),
                text=text, confidence=float(confidence)
            )
            boxes.append(box)

        return Boundboxes(boxes)

    def process_multiple(self, image_paths) -> list[Boundboxes]:
        """
        Process multiple images and return list of Boundboxes.

        Args:
            image_paths: List of image file paths

        Returns:
            List of Boundboxes instances
        """
        results = []
        for image_path in image_paths:
            print(f"📄 Processing: {Path(image_path).name}")
            boundboxes = self(image_path)
            print(f"✅ Extracted {len(boundboxes.boxes)} detections")
            results.append(boundboxes)
        return results

    def set_content_filter(self, x1, x2, y1, y2):
        """
        Update content area filter boundaries.
        """
        self.filter_x1 = x1
        self.filter_x2 = x2
        self.filter_y1 = y1
        self.filter_y2 = y2
        print(f"📐 Content filter updated: ({x1}, {y1}) -> ({x2}, {y2})")

    def disable_content_filter(self):
        """
        Disable content area filtering.
        """
        self.content_filter = False
        print("🔓 Content filtering disabled")

    def enable_content_filter(self):
        """
        Enable content area filtering.
        """
        self.content_filter = True
        print("🔒 Content filtering enabled")