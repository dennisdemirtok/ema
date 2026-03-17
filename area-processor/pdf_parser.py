"""
PDF Vector Extraction using PyMuPDF.
Extracts lines, text blocks, and metadata from architectural PDF drawings.
"""

import re
import fitz  # PyMuPDF
import numpy as np
from dataclasses import dataclass, field
from config import WALL_STROKE_MIN, KNOWN_SCALES, DEFAULT_SCALE


@dataclass
class Line:
    """A line segment from the PDF."""
    x0: float
    y0: float
    x1: float
    y1: float
    width: float
    color: tuple = (0, 0, 0)

    @property
    def length(self) -> float:
        return np.sqrt((self.x1 - self.x0) ** 2 + (self.y1 - self.y0) ** 2)

    @property
    def midpoint(self) -> tuple:
        return ((self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2)


@dataclass
class TextBlock:
    """A text block from the PDF with its position."""
    text: str
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def center(self) -> tuple:
        return ((self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2)


@dataclass
class PDFData:
    """Extracted data from a PDF page."""
    page_width: float = 0
    page_height: float = 0
    lines: list = field(default_factory=list)
    wall_lines: list = field(default_factory=list)
    text_blocks: list = field(default_factory=list)
    room_labels: list = field(default_factory=list)
    scale: int = DEFAULT_SCALE
    pts_to_m: float = 0.00352778  # Default for 1:100


def extract_pdf_data(pdf_path: str, page_num: int = 0) -> PDFData:
    """Extract vector data, text, and metadata from a PDF page."""
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    data = PDFData()

    # Page dimensions
    rect = page.rect
    data.page_width = rect.width
    data.page_height = rect.height

    # Extract all drawings (vector paths)
    drawings = page.get_drawings()
    for d in drawings:
        color = d.get("color", (0, 0, 0)) or (0, 0, 0)
        width = d.get("width", 0) or 0

        for item in d.get("items", []):
            if item[0] == "l":  # Line segment
                p1, p2 = item[1], item[2]
                line = Line(
                    x0=p1.x, y0=p1.y,
                    x1=p2.x, y1=p2.y,
                    width=width,
                    color=color
                )
                data.lines.append(line)

                # Classify as wall if thick enough
                if width >= WALL_STROKE_MIN and line.length > 5:
                    data.wall_lines.append(line)

            elif item[0] == "re":  # Rectangle
                r = item[1]
                # Add as 4 lines
                corners = [
                    (r.x0, r.y0), (r.x1, r.y0),
                    (r.x1, r.y1), (r.x0, r.y1)
                ]
                for i in range(4):
                    j = (i + 1) % 4
                    line = Line(
                        x0=corners[i][0], y0=corners[i][1],
                        x1=corners[j][0], y1=corners[j][1],
                        width=width,
                        color=color
                    )
                    data.lines.append(line)
                    if width >= WALL_STROKE_MIN:
                        data.wall_lines.append(line)

    # Extract text blocks
    text_dict = page.get_text("dict")
    for block in text_dict.get("blocks", []):
        if block.get("type") == 0:  # Text block
            for line in block.get("lines", []):
                text = ""
                for span in line.get("spans", []):
                    text += span.get("text", "")

                if text.strip():
                    bbox = line.get("bbox", block.get("bbox", (0, 0, 0, 0)))
                    tb = TextBlock(
                        text=text.strip(),
                        x0=bbox[0], y0=bbox[1],
                        x1=bbox[2], y1=bbox[3]
                    )
                    data.text_blocks.append(tb)

    # Detect scale
    data.scale = detect_scale(data.text_blocks)
    data.pts_to_m = 0.352778 / data.scale  # mm per pt / scale

    # Identify room labels (text that looks like room names)
    data.room_labels = identify_room_labels(data.text_blocks)

    doc.close()
    return data


def detect_scale(text_blocks: list) -> int:
    """Detect the drawing scale from text content."""
    scale_pattern = re.compile(r"1\s*:\s*(\d+)")

    for tb in text_blocks:
        match = scale_pattern.search(tb.text)
        if match:
            scale_val = int(match.group(1))
            if scale_val in KNOWN_SCALES:
                return scale_val

    return DEFAULT_SCALE


def identify_room_labels(text_blocks: list) -> list:
    """
    Identify text blocks that are likely room names/labels.
    Filters out dimension text, door labels, scale text, etc.
    """
    # Patterns to exclude
    exclude_patterns = [
        re.compile(r"^\d+$"),  # Pure numbers
        re.compile(r"^\d+\s*:\s*\d+$"),  # Scale notation
        re.compile(r"^[A-Z]-\d+"),  # Drawing numbers
        re.compile(r"^D\d+"),  # Door labels
        re.compile(r"^\d+x\d+"),  # Door dimensions
        re.compile(r"^±"),  # Elevation markers
        re.compile(r"^\+\d"),  # Level markers
        re.compile(r"^REV"),  # Revision labels
        re.compile(r"^\d+\.\d+ m"),  # Dimension labels
    ]

    room_labels = []
    for tb in text_blocks:
        text = tb.text.strip()

        # Skip very short or very long text
        if len(text) < 2 or len(text) > 50:
            continue

        # Skip excluded patterns
        excluded = False
        for pattern in exclude_patterns:
            if pattern.match(text):
                excluded = True
                break

        if not excluded:
            # Likely a room label if it contains letters and isn't technical
            if any(c.isalpha() for c in text):
                room_labels.append(tb)

    return room_labels
