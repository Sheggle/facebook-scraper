from pydantic import BaseModel
from typing import Self


class Boundbox(BaseModel):
    x1: int
    x2: int
    y1: int
    y2: int

    @property
    def width(self):
        return self.x2 - self.x1
    
    @property
    def height(self):
        return self.y2 - self.y1
    

class Boundboxes:
    def __init__(self, boxes: list[Boundbox]) -> None:
        self.boxes = boxes

    def pop_top_line(self) -> Self:
        ...

    def pop_bottom_line(self) -> Self:
        ...

    def concat_boxes(self, respect_newline) -> Self:
        ...

    def remove_matching(self, text: str, case_sensitive=False):
        ...

    def remove_duplicates(self, min_ratio: float):
        ...
