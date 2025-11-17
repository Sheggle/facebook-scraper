"""
Facebook scraper package for OCR processing and content extraction.

This package contains modules for:
- OCR processing of Facebook screenshots
- Bounding box management and operations
- Image alignment algorithms
- Content parsing from OCR results
"""

# Import main components for easy access
from .ocr import main as ocr_main
from .boundboxes import Boundboxes, Boundbox
from .content_parser import parse_comment, parse_post
from .image_alignment import find_alignment_offsets_boundboxes, text_similarity
from .image_processing import align_and_combine_images, draw_bounding_boxes_on_combined
from .facebook_processing import shade_comment_regions
from .easy_ocr import EasyOCR

__all__ = [
    'ocr_main',
    'Boundboxes',
    'Boundbox',
    'parse_comment',
    'parse_post',
    'find_alignment_offsets_boundboxes',
    'text_similarity',
    'align_and_combine_images',
    'draw_bounding_boxes_on_combined',
    'shade_comment_regions',
    'EasyOCR'
]