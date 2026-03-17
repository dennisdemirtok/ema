"""
PDF Result Generator.
Takes the original PDF and overlays pink/rosa room polygons with "Undertak X,XX m²" labels.
Styled to match professional Swedish ceiling plan (undertaksritning) output.
"""

import fitz  # PyMuPDF
from room_detector import Room


# Pink/Rosa color for all rooms (matches reference style)
ROOM_FILL_COLOR = (1.0, 0.75, 0.8)  # Pink/rosa
ROOM_BORDER_COLOR = (0.85, 0.45, 0.55)  # Darker pink for border
OVERLAY_OPACITY = 0.4
LABEL_FONT_SIZE = 9
LABEL_COLOR = (0.1, 0.1, 0.1)  # Near-black text
AREA_COLOR = (0.15, 0.15, 0.4)  # Dark blue for area numbers


def generate_result_pdf(input_path: str, output_path: str, rooms: list,
                        page_num: int = 0) -> str:
    """
    Generate a result PDF with pink room overlays and "Undertak X,XX m²" labels.

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

    for room in rooms:
        if len(room.polygon_pts) < 3:
            continue

        # Draw filled polygon in pink
        points = [fitz.Point(p[0], p[1]) for p in room.polygon_pts]
        shape = page.new_shape()
        shape.draw_polyline(points + [points[0]])
        shape.finish(
            color=ROOM_BORDER_COLOR,
            fill=ROOM_FILL_COLOR,
            fill_opacity=OVERLAY_OPACITY,
            width=0.5,
            stroke_opacity=0.6,
        )
        shape.commit()

        # Add label: "Undertak\nXX,XX m²" at centroid
        cx, cy = room.centroid_pts

        # Format area with comma (Swedish format)
        area_str = f"{room.area_m2:.2f}".replace(".", ",")

        name_text = room.name or ""
        undertak_text = "Undertak"
        area_text = f"{area_str} m²"

        # Calculate label dimensions
        lines_count = 3 if name_text else 2
        max_text = max(len(undertak_text), len(area_text), len(name_text) if name_text else 0)
        text_width = max(max_text * LABEL_FONT_SIZE * 0.52, 50)
        text_height = LABEL_FONT_SIZE * (lines_count + 0.8)

        label_rect = fitz.Rect(
            cx - text_width / 2,
            cy - text_height / 2,
            cx + text_width / 2,
            cy + text_height / 2,
        )

        # White label background
        bg_shape = page.new_shape()
        bg_shape.draw_rect(label_rect)
        bg_shape.finish(
            color=(0.7, 0.7, 0.7),
            fill=(1, 1, 1),
            fill_opacity=0.9,
            width=0.3,
        )
        bg_shape.commit()

        # Text positioning
        left_x = cx - text_width / 2 + 3
        current_y = cy - text_height / 2 + LABEL_FONT_SIZE + 1

        if name_text:
            # Room name (e.g., "Kontor A")
            page.insert_text(
                fitz.Point(left_x, current_y),
                name_text,
                fontsize=LABEL_FONT_SIZE - 1,
                fontname="helv",
                color=LABEL_COLOR,
            )
            current_y += LABEL_FONT_SIZE + 1

        # "Undertak"
        page.insert_text(
            fitz.Point(left_x, current_y),
            undertak_text,
            fontsize=LABEL_FONT_SIZE,
            fontname="hebo",  # Helvetica Bold
            color=LABEL_COLOR,
        )
        current_y += LABEL_FONT_SIZE + 1

        # Area value (e.g., "15,75 m²")
        page.insert_text(
            fitz.Point(left_x, current_y),
            area_text,
            fontsize=LABEL_FONT_SIZE,
            fontname="helv",
            color=AREA_COLOR,
        )

    doc.save(output_path)
    doc.close()

    return output_path
