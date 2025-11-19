#!/usr/bin/env python3
"""
Tesseract OCR wrapper that outputs Boundboxes directly.
"""

import pytesseract
from PIL import Image
from pathlib import Path
from .boundboxes import Boundboxes, Boundbox


class TesseractOCR:
    """
    Tesseract OCR wrapper that processes images and returns Boundboxes with optional content filtering.
    """

    def __init__(self, languages=['eng', 'nld'], content_filter=True,
                 filter_x1=280, filter_x2=1020, filter_y1=90, filter_y2=580):
        """
        Initialize Tesseract OCR.

        Args:
            languages: List of language codes for OCR recognition ('eng' for English, 'nld' for Dutch)
            content_filter: Whether to apply content area filtering
            filter_x1, filter_x2, filter_y1, filter_y2: Content area boundaries
        """
        print(f"🔍 Initializing Tesseract OCR ({' + '.join(languages)})...")
        self.languages = '+'.join(languages)
        self.content_filter = content_filter
        self.filter_x1 = filter_x1
        self.filter_x2 = filter_x2
        self.filter_y1 = filter_y1
        self.filter_y2 = filter_y2

        # Configure Tesseract for better accuracy
        self.config = '--oem 3 --psm 6'  # LSTM OCR Engine Mode, single uniform block

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

        # Load image
        try:
            image = Image.open(image_path)
        except Exception as e:
            print(f"❌ Failed to load image {image_path}: {e}")
            return Boundboxes([])

        # Run OCR on the image
        try:
            data = pytesseract.image_to_data(
                image,
                lang=self.languages,
                config=self.config,
                output_type=pytesseract.Output.DICT
            )
        except Exception as e:
            print(f"❌ Tesseract OCR failed on {image_path}: {e}")
            return Boundboxes([])

        # Convert to Boundboxes
        boxes = []
        n_boxes = len(data['text'])

        for i in range(n_boxes):
            # Skip empty detections
            text = data['text'][i].strip()
            if not text:
                continue

            # Get bounding box coordinates
            x1 = data['left'][i]
            y1 = data['top'][i]
            width = data['width'][i]
            height = data['height'][i]
            x2 = x1 + width
            y2 = y1 + height

            # Get confidence (convert from 0-100 scale to 0-1 scale)
            confidence = data['conf'][i] / 100.0 if data['conf'][i] > 0 else 0.0

            # Skip very low confidence detections
            if confidence < 0.1:
                continue

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
        print(f"📐 Updated content filter: ({x1}, {y1}) -> ({x2}, {y2})")

    def set_languages(self, languages):
        """
        Update OCR languages.

        Args:
            languages: List of language codes ('eng', 'nld', etc.)
        """
        self.languages = '+'.join(languages)
        print(f"🌐 Updated languages: {self.languages}")

    def set_config(self, config):
        """
        Update Tesseract configuration string.

        Args:
            config: Tesseract config string (e.g., '--oem 3 --psm 6')
        """
        self.config = config
        print(f"⚙️ Updated Tesseract config: {config}")