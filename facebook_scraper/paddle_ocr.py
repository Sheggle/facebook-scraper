#!/usr/bin/env python3
"""
Minimal PaddleOCR wrapper that outputs Boundboxes directly.
Based on working 10-line script that produces good output.
"""

from paddleocr import PaddleOCR
from pathlib import Path
from .boundboxes import Boundboxes, Boundbox


class PaddleOCRWrapper:
    """
    Minimal PaddleOCR wrapper that processes images and returns Boundboxes.
    """

    def __init__(self, languages=['en', 'nl']):
        """
        Initialize PaddleOCR with minimal configuration.

        Args:
            languages: List of language codes for OCR recognition
        """
        print(f"🔍 Initializing PaddleOCR ({' + '.join(languages)})...")

        # Initialize PaddleOCR with working configuration from 10-line script
        self.ocr = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            lang='en'  # Use English as primary language
        )

    def __call__(self, image_path: str) -> Boundboxes:
        """
        Process an image and return Boundboxes.

        Args:
            image_path: Path to the image file

        Returns:
            Boundboxes instance containing detected text boxes
        """
        image_path_obj = Path(image_path)

        if not image_path_obj.exists():
            print(f"❌ Image not found: {image_path}")
            return Boundboxes([])

        # Run OCR using the same method as working 10-line script
        try:
            result = self.ocr.predict(input=str(image_path))
        except Exception as e:
            print(f"❌ PaddleOCR failed on {image_path}: {e}")
            return Boundboxes([])

        # Convert PaddleOCR results to Boundboxes
        boxes = []
        for res in result:
            # Extract from PaddleOCR result format (seen in working script output)
            res_dict = res['res'] if isinstance(res, dict) and 'res' in res else res

            if 'rec_polys' in res_dict and 'rec_texts' in res_dict and 'rec_scores' in res_dict:
                polys = res_dict['rec_polys']
                texts = res_dict['rec_texts']
                scores = res_dict['rec_scores']

                for poly, text, score in zip(polys, texts, scores):
                    text = text.strip() if text else ""

                    if not text:
                        continue

                    # Extract coordinates from polygon (4 points: [[x1,y1], [x2,y1], [x2,y2], [x1,y2]])
                    x1 = min(point[0] for point in poly)
                    y1 = min(point[1] for point in poly)
                    x2 = max(point[0] for point in poly)
                    y2 = max(point[1] for point in poly)

                    # Use actual confidence score
                    confidence = float(score) if score is not None else 0.9

                    box = Boundbox(
                        x1=float(x1), y1=float(y1), x2=float(x2), y2=float(y2),
                        text=text, confidence=confidence
                    )
                    boxes.append(box)

        return Boundboxes(boxes)


if __name__ == '__main__':
    # Test with working configuration from 10-line script
    from paddleocr import PaddleOCR

    ocr = PaddleOCR(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False)

    # Test on sample image
    result = ocr.predict(
        input="https://paddle-model-ecology.bj.bcebos.com/paddlex/imgs/demo_image/general_ocr_002.png")

    # Print results
    for res in result:
        res.print()
        res.save_to_img("output")
        res.save_to_json("output")