"""
PDF Result Generator.
Takes the original PDF and overlays colored room polygons with area labels.
"""

import fitz  # PyMuPDF
from room_detector import Room


# Color palette for rooms (RGBA, alpha 0.3 for transparency)
ROOM_COLORS = [
    (0.5, 0.5, 1.0),    # Blue
    (0.5, 1.0, 0.5),    # Green
    (1.0, 0.8, 0.4),    # Orange
    (0.8, 0.5, 1.0),    # Purple
    (0.4, 0.9, 0.9),    # Cyan
    (1.0, 0.6, 0.6),    # Red
    (0.7, 1.0, 0.4),    # Lime
    (1.0, 0.7, 0.9),    # Pink
    (0.6, 0.8, 1.0),    # Light blue
    (1.0, 1.0, 0.5),    # Yellow
]

OVERLAY_OPACITY = 0.35
LABEL_FONT_SIZE = 10
LABEL_COLOR = (0, 0, 0)  # Black text
LABEL_BG_COLOR = (1, 1, 1)  # White background


def generate_result_pdf(input_path: str, output_path: str, rooms: list,
                        page_num: int = 0) -> str:
    """
    Generate a result PDF with colored room overlays and area labels.

    Args:
        input_path: Path to original PDF
        output_path: Path to save result PDF
        rooms: List of Room objects
        page_num: Which page to annotate

    Returns:
        Path to the generated PDF
    """
    doc = fitz.open(input_path)
    page = doc[page_num]

    for i, room in enumerate(rooms):
        color = ROOM_COLORS[i % len(ROOM_COLORS)]

        if len(room.polygon_pts) < 3:
            continue

        # Draw filled polygon
        points = [fitz.Point(p[0], p[1]) for p in room.polygon_pts]
        shape = page.new_shape()

        # Draw polygon path
        shape.draw_polyline(points + [points[0]])
        shape.finish(
            color=color,
            fill=color,
            fill_opacity=OVERLAY_OPACITY,
            width=0.5,
            stroke_opacity=0.7,
        )
        shape.commit()

        # Add area label at centroid
        cx, cy = room.centroid_pts
        area_text = f"{room.area_m2:.2f} m²"
        name_text = room.name or ""

        # Calculate label position and size
        if name_text:
            full_text = f"{name_text}\n{area_text}"
        else:
            full_text = area_text

        # Create label background
        font_size = LABEL_FONT_SIZE
        text_width = max(len(name_text), len(area_text)) * font_size * 0.5
        text_height = font_size * (2.5 if name_text else 1.5)

        label_rect = fitz.Rect(
            cx - text_width / 2,
            cy - text_height / 2,
            cx + text_width / 2,
            cy + text_height / 2,
        )

        # White background with slight transparency
        bg_shape = page.new_shape()
        bg_shape.draw_rect(label_rect)
        bg_shape.finish(
            color=(0.3, 0.3, 0.3),
            fill=(1, 1, 1),
            fill_opacity=0.85,
            width=0.3,
        )
        bg_shape.commit()

        # Add text
        if name_text:
            # Room name (bold)
            name_point = fitz.Point(cx - text_width / 2 + 4, cy - 2)
            page.insert_text(
                name_point,
                name_text,
                fontsize=font_size,
                fontname="helv",
                color=(0, 0, 0),
            )

            # Area value
            area_point = fitz.Point(cx - text_width / 2 + 4, cy + font_size + 2)
            page.insert_text(
                area_point,
                area_text,
                fontsize=font_size - 1,
                fontname="helv",
                color=(0.2, 0.2, 0.5),
            )
        else:
            # Just area
            area_point = fitz.Point(cx - text_width / 2 + 4, cy + font_size / 2)
            page.insert_text(
                area_point,
                area_text,
                fontsize=font_size,
                fontname="helv",
                color=(0, 0, 0),
            )

    doc.save(output_path)
    doc.close()

    return output_path
