#!/usr/bin/env python3
"""
Rerun OCR processing on all existing screenshot directories.

This script processes all directories in the screenshots/ folder,
allowing you to iterate on OCR parsing logic with consistent input data
without having to re-scrape Facebook.
"""

import os
import subprocess
import shutil
import json
from pathlib import Path
from datetime import datetime

def main():
    screenshots_dir = Path('screenshots')
    annotated_dir = Path('annotated')
    storage_dir = Path('storage2')

    if not screenshots_dir.exists():
        print(f"❌ Screenshots directory not found: {screenshots_dir}")
        return

    # Get all screenshot directories
    screenshot_dirs = [d for d in screenshots_dir.iterdir() if d.is_dir()]

    if not screenshot_dirs:
        print(f"❌ No directories found in {screenshots_dir}")
        return

    print(f"📸 Found {len(screenshot_dirs)} screenshot directories to process")

    # Clean up any existing directories
    if annotated_dir.exists():
        print(f"🧹 Cleaning existing {annotated_dir}")
        shutil.rmtree(annotated_dir)

    if storage_dir.exists():
        print(f"🧹 Cleaning existing {storage_dir}")
        shutil.rmtree(storage_dir)

    # Create fresh storage directory
    storage_dir.mkdir(exist_ok=True)

    # Process each directory
    for i, screenshot_dir in enumerate(screenshot_dirs, 1):
        print(f"\n[{i}/{len(screenshot_dirs)}] Processing: {screenshot_dir.name}")

        # Count images in directory
        image_files = list(screenshot_dir.glob("*.png"))
        print(f"   📄 Found {len(image_files)} PNG files")

        if not image_files:
            print(f"   ⚠️  No PNG files found, skipping")
            continue

        # Run OCR processing
        cmd = ['uv', 'run', 'run_ocr.py', str(screenshot_dir)]
        try:
            result = subprocess.run(cmd, text=True)

            if result.returncode == 0:
                print(f"   ✅ OCR processing completed successfully")

                # Check if output files were created and copy to storage
                output_dir = annotated_dir / screenshot_dir.name
                if output_dir.exists():
                    json_file = output_dir / "parsed_data.json"
                    if json_file.exists():
                        print(f"   📄 Output saved to: {json_file}")

                        # Copy to storage2 with enhanced metadata
                        try:
                            with open(json_file, 'r') as f:
                                data = json.load(f)

                            # Add metadata (similar to main.py logic)
                            data['screenshot_dir'] = screenshot_dir.name
                            data['reprocess_date'] = str(datetime.now())

                            storage_file = storage_dir / f"{screenshot_dir.name}.json"
                            with open(storage_file, 'w') as f:
                                json.dump(data, f, indent=2)

                            print(f"   💾 Copied to storage: {storage_file}")

                        except Exception as e:
                            print(f"   ❌ Failed to copy to storage: {e}")
                    else:
                        print(f"   ⚠️  No parsed_data.json found in output")
                else:
                    print(f"   ⚠️  No output directory created")
            else:
                print(f"   ❌ OCR processing failed with return code: {result.returncode}")

        except Exception as e:
            print(f"   ❌ Failed to run OCR: {e}")

    print(f"\n🎉 Completed processing {len(screenshot_dirs)} directories")
    print(f"📁 Detailed results available in: {annotated_dir}")

    # Count successful storage copies
    storage_files = list(storage_dir.glob("*.json"))
    print(f"💾 Copied {len(storage_files)} parsed results to: {storage_dir}")

    if len(storage_files) != len(screenshot_dirs):
        print(f"⚠️  Note: {len(screenshot_dirs) - len(storage_files)} directories failed processing")

if __name__ == "__main__":
    main()