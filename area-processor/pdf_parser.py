"""
PDF Vector Extraction using PyMuPDF.
Extracts lines, text blocks, and metadata from architectural PDF drawings.
"""

import re
import fitz  # PyMuPDF
import numpy as np
from dataclasses import dataclass, field
from config import KNOWN_SCALES, DEFAULT_SCALE

# Min length for a line to be considered structural (walls, borders)
MIN_WALL_LENGTH = 5.0
# Max length for a wall line (very long = probably page border)
MAX_WALL_LENGTH_RATIO = 0.8  # fraction of page diagonal


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
    pts_to_m: float = 0.0352778  # Default for 1:100 (1pt = 0.352778mm * 100 / 1000)
    pdf_path: str = ""  # Store path for rasterization


def extract_pdf_data(pdf_path: str, page_num: int = 0) -> PDFData:
    """Extract vector data, text, and metadata from a PDF page."""
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    data = PDFData()
    data.pdf_path = pdf_path

    # Page dimensions
    rect = page.rect
    data.page_width = rect.width
    data.page_height = rect.height
    page_diagonal = np.sqrt(rect.width ** 2 + rect.height ** 2)
    max_wall_length = page_diagonal * MAX_WALL_LENGTH_RATIO

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

                # Include as wall line if reasonable length
                # CAD exports often have width=0 for all lines
                if MIN_WALL_LENGTH < line.length < max_wall_length:
                    data.wall_lines.append(line)

            elif item[0] == "re":  # Rectangle
                r = item[1]
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
                    if MIN_WALL_LENGTH < line.length < max_wall_length:
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
    data.pts_to_m = 0.352778 * data.scale / 1000  # mm per pt * scale / 1000 → meters

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
    Uses a whitelist approach: only text matching known Swedish room name patterns
    is included. This avoids false positives from window labels, duct marks, etc.
    """
    # Known Swedish room name patterns (case-insensitive matching)
    room_patterns = [
        re.compile(r"(?i)kontor"),
        re.compile(r"(?i)konferens"),
        re.compile(r"(?i)k[öo]k"),
        re.compile(r"(?i)wc"),
        re.compile(r"(?i)rwc"),
        re.compile(r"(?i)toalett"),
        re.compile(r"(?i)bad(rum)?"),
        re.compile(r"(?i)dusch"),
        re.compile(r"(?i)sovrum"),
        re.compile(r"(?i)vardagsrum"),
        re.compile(r"(?i)allrum"),
        re.compile(r"(?i)hall\b"),
        re.compile(r"(?i)entr[eé]"),
        re.compile(r"(?i)korridor"),
        re.compile(r"(?i)passage"),
        re.compile(r"(?i)trapphus"),
        re.compile(r"(?i)hiss\b"),
        re.compile(r"(?i)förr[aå]d"),
        re.compile(r"(?i)städ"),
        re.compile(r"(?i)tvätt"),
        re.compile(r"(?i)klädkammare"),
        re.compile(r"(?i)klkm"),
        re.compile(r"(?i)balkong"),
        re.compile(r"(?i)terrass"),
        re.compile(r"(?i)uteplats"),
        re.compile(r"(?i)pausrum"),
        re.compile(r"(?i)samtalsrum"),
        re.compile(r"(?i)mötesrum"),
        re.compile(r"(?i)fikarum"),
        re.compile(r"(?i)lunchrum"),
        re.compile(r"(?i)personalrum"),
        re.compile(r"(?i)vilrum"),
        re.compile(r"(?i)studio"),
        re.compile(r"(?i)storkontor"),
        re.compile(r"(?i)reception"),
        re.compile(r"(?i)v[aä]ntrum"),
        re.compile(r"(?i)arkiv"),
        re.compile(r"(?i)server"),
        re.compile(r"(?i)teknik"),
        re.compile(r"(?i)elc\b"),
        re.compile(r"(?i)fläkt"),
        re.compile(r"(?i)rum\b"),
        re.compile(r"(?i)lgh\b"),
        re.compile(r"(?i)garage"),
        re.compile(r"(?i)cykel"),
        re.compile(r"(?i)bef\s"),  # "Bef kontor", "Bef konferens"
        re.compile(r"(?i)oidentifierade"),  # "Oidentifierade utrymmen"
        re.compile(r"(?i)skrivare"),  # "Skrivare/frd"
        re.compile(r"(?i)utrymm"),  # "Utrymme", "Utrymmen"
    ]

    # Minimum text block height to filter out tiny annotation text
    MIN_LABEL_HEIGHT = 7.0  # points

    room_labels = []
    for tb in text_blocks:
        text = tb.text.strip()
        text_height = tb.y1 - tb.y0

        # Skip very small text (window marks, duct labels, etc.)
        if text_height < MIN_LABEL_HEIGHT:
            continue

        # Skip very short or very long text
        if len(text) < 2 or len(text) > 40:
            continue

        # Check if text matches any room name pattern
        for pattern in room_patterns:
            if pattern.search(text):
                room_labels.append(tb)
                break

    return room_labels
