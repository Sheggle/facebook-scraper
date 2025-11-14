from pydantic import BaseModel
from typing import Self
import re
import statistics
from difflib import SequenceMatcher


class Boundbox(BaseModel):
    x1: float
    x2: float
    y1: float
    y2: float
    text: str
    confidence: float

    @property
    def width(self):
        return self.x2 - self.x1

    @property
    def height(self):
        return self.y2 - self.y1

    @property
    def area(self):
        return self.width * self.height
    

class Boundboxes:
    def __init__(self, boxes: list[Boundbox]) -> None:
        self.boxes = boxes


    def apply_offset(self, y_offset: float) -> Self:
        """Return new Boundboxes with Y coordinates adjusted by offset."""
        adjusted_boxes = []
        for box in self.boxes:
            adjusted_box = box.model_copy()
            adjusted_box.y1 += y_offset
            adjusted_box.y2 += y_offset
            adjusted_boxes.append(adjusted_box)
        return self.__class__(adjusted_boxes)

    def filter_content_area(self) -> Self:
        """Return new Boundboxes with only content area boxes."""
        filtered_boxes = []
        for box in self.boxes:
            if (280 <= box.x1 and box.x2 <= 1020 and
                90 <= box.y1 and box.y2 <= 580):
                filtered_boxes.append(box)
        return self.__class__(filtered_boxes)

    def remove_duplicates(self, min_ratio: float = 0.5) -> Self:
        """Remove smaller bounding boxes that are covered by more than min_ratio by larger ones."""
        if not self.boxes:
            return self.__class__([])

        # Sort by y1 for efficient overlap checking
        sorted_boxes = sorted(self.boxes, key=lambda x: x.y1)
        keep_indices = set(range(len(sorted_boxes)))

        for i in range(len(sorted_boxes)):
            if i not in keep_indices:
                continue

            box1 = sorted_boxes[i]

            for j in range(i + 1, len(sorted_boxes)):
                if j not in keep_indices:
                    continue

                box2 = sorted_boxes[j]

                # Early termination: if box2.y1 >= box1.y2, no more overlaps possible
                if box2.y1 >= box1.y2:
                    break

                # Check Y-overlap condition
                if box2.y2 <= box1.y1:
                    continue

                # Calculate intersection
                x_overlap = max(0, min(box1.x2, box2.x2) - max(box1.x1, box2.x1))
                y_overlap = max(0, min(box1.y2, box2.y2) - max(box1.y1, box2.y1))
                intersection = x_overlap * y_overlap

                # Check if smaller box is covered by more than min_ratio
                if box1.area < box2.area:
                    coverage = intersection / box1.area if box1.area > 0 else 0
                    if coverage > min_ratio:
                        keep_indices.discard(i)
                        break
                else:
                    coverage = intersection / box2.area if box2.area > 0 else 0
                    if coverage > min_ratio:
                        keep_indices.discard(j)

        # Return only kept boxes
        deduplicated_boxes = [sorted_boxes[i] for i in keep_indices]
        return self.__class__(deduplicated_boxes)

    def pop_top_line(self) -> Self:
        """Return new Boundboxes with top row (within 10px of min y1)."""
        if not self.boxes:
            return self.__class__([])

        min_y1 = min(box.y1 for box in self.boxes)
        top_boxes = [box for box in self.boxes if box.y1 <= min_y1 + 10]
        return self.__class__(top_boxes)

    def pop_bottom_line(self) -> Self:
        """Return new Boundboxes with bottom row (within 10px of max y1)."""
        if not self.boxes:
            return self.__class__([])

        max_y1 = max(box.y1 for box in self.boxes)
        bottom_boxes = [box for box in self.boxes if box.y1 >= max_y1 - 10]
        return self.__class__(bottom_boxes)

    def remove_matching(self, patterns, case_sensitive=False) -> Self:
        """Return new Boundboxes with boxes matching patterns removed."""
        if isinstance(patterns, str):
            patterns = [patterns]

        filtered_boxes = []
        for box in self.boxes:
            text = box.text if case_sensitive else box.text.lower()
            should_keep = True

            for pattern in patterns:
                pattern_text = pattern if case_sensitive else pattern.lower()
                if pattern_text in text:
                    should_keep = False
                    break

            if should_keep:
                filtered_boxes.append(box)

        return self.__class__(filtered_boxes)

    def create_readable_text(self) -> str:
        """Process boxes row by row to create readable text."""
        if not self.boxes:
            return ""

        remaining_boxes = self.boxes.copy()
        text_lines = []

        while remaining_boxes:
            # Find minimum y1 in remaining boxes
            min_y1 = min(box.y1 for box in remaining_boxes)

            # Get current row (boxes within 10px of min_y1)
            current_row = [box for box in remaining_boxes if box.y1 <= min_y1 + 10]

            # Sort current row by x1 coordinate (left to right)
            current_row.sort(key=lambda box: box.x1)

            # Extract text from current row
            row_text = " ".join(box.text for box in current_row)
            text_lines.append(row_text)

            # Remove processed boxes from remaining_boxes
            for box in current_row:
                remaining_boxes.remove(box)

        return " ".join(text_lines)

    def find_pattern(self, regex_pattern: str) -> Boundbox | None:
        """Find first box matching regex pattern."""
        pattern = re.compile(regex_pattern)
        for box in self.boxes:
            if pattern.match(box.text.strip()):
                return box
        return None

    def find_boxes_above(self, y_coord: float, margin: int = 10) -> Self:
        """Get boxes with y1 at least margin pixels above y_coord."""
        filtered_boxes = [box for box in self.boxes if box.y1 <= y_coord - margin]
        return self.__class__(filtered_boxes)

    def find_boxes_in_region(self, start_y: float, end_y: float) -> Self:
        """Get boxes within Y range."""
        filtered_boxes = [box for box in self.boxes if start_y <= box.y1 <= end_y]
        return self.__class__(filtered_boxes)

    def exclude_top_and_bottom_lines(self) -> Self:
        """Return boxes that are not in top or bottom lines."""
        if not self.boxes:
            return self.__class__([])

        min_y1 = min(box.y1 for box in self.boxes)
        max_y1 = max(box.y1 for box in self.boxes)

        middle_boxes = []
        for box in self.boxes:
            # Skip if it's in top row or bottom row
            if (box.y1 <= min_y1 + 10) or (box.y1 >= max_y1 - 10):
                continue
            middle_boxes.append(box)

        return self.__class__(middle_boxes)

    def sort_by_coordinates(self) -> Self:
        """Return new Boundboxes sorted by x1 coordinate."""
        sorted_boxes = sorted(self.boxes, key=lambda box: box.x1)
        return self.__class__(sorted_boxes)

    def to_text_line(self) -> str:
        """Join all box texts with spaces, sorted by x1."""
        if not self.boxes:
            return ""
        sorted_boxes = sorted(self.boxes, key=lambda box: box.x1)
        return " ".join(box.text for box in sorted_boxes)
