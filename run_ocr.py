#!/usr/bin/env python3
"""
Entry point script for running OCR processing on Facebook screenshots.
This script imports and runs the main OCR functionality from the facebook_scraper package.
"""

import sys
from facebook_scraper.ocr import main

if __name__ == "__main__":
    main()