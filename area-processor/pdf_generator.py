"""
PDF Result Generator.
Takes the original PDF and overlays pink/rosa room polygons with "Undertak X,XX m²" labels.
Styled to match professional Swedish ceiling plan (undertaksritning) output.
"""

import fitz  # PyMuPDF
from room_detector import Room


# Pink/Rosa color for all rooms (matches reference style)
ROOM_FILL_COLOR = (1.0, 0.75, 0.80)  # Pink/rosa - clearly visible
ROOM_BORDER_COLOR = (0.80, 0.40, 0.55)  # Darker pink for border
LABEL_FONT_SIZE = 9
LABEL_COLOR = (0.1, 0.1, 0.1)  # Near-black text
AREA_COLOR = (0.15, 0.15, 0.4)  # Dark blue for area numbers


def generate_result_pdf(input_path: str, output_path: str, rooms: list,
                        page_num: int = 0) -> str:
    """
    Generate a result PDF with pink room overlays and "Undertak X,XX m²" labels.
    """
    doc = fitz.open(input_path)
    page = doc[page_num]

    # ── STEP 1: Draw all room fills (largest first, so smaller rooms paint on top) ──
    rooms_sorted = sorted(rooms, key=lambda r: -r.area_m2)

    for room in rooms_sorted:
        if len(room.polygon_pts) < 3:
            continue

        p = room.polygon_pts
        rx0, ry0 = p[0]
        rx1, ry1 = p[2]

        rect = fitz.Rect(rx0, ry0, rx1, ry1)
        shape = page.new_shape()
        shape.draw_rect(rect)
        shape.finish(
            color=None,  # No border for fill layer
            fill=ROOM_FILL_COLOR,
            fill_opacity=0.45,
            width=0,
        )
        shape.commit()

    # ── STEP 2: Draw room borders (thin lines to show room boundaries) ──
    for room in rooms_sorted:
        if len(room.polygon_pts) < 3:
            continue

        p = room.polygon_pts
        rx0, ry0 = p[0]
        rx1, ry1 = p[2]

        rect = fitz.Rect(rx0, ry0, rx1, ry1)
        shape = page.new_shape()
        shape.draw_rect(rect)
        shape.finish(
            color=ROOM_BORDER_COLOR,
            fill=None,  # No fill, just border
            width=0.5,
            stroke_opacity=0.5,
        )
        shape.commit()

    # ── STEP 3: Draw labels on top of everything ──
    for room in rooms_sorted:
        if len(room.polygon_pts) < 3:
            continue

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
            fill_opacity=0.92,
            width=0.3,
        )
        bg_shape.commit()

        # Text positioning
        left_x = cx - text_width / 2 + 3
        current_y = cy - text_height / 2 + LABEL_FONT_SIZE + 1

        if name_text:
            page.insert_text(
                fitz.Point(left_x, current_y),
                name_text,
                fontsize=LABEL_FONT_SIZE - 1,
                fontname="helv",
                color=LABEL_COLOR,
            )
            current_y += LABEL_FONT_SIZE + 1

        # "Undertak" in bold
        page.insert_text(
            fitz.Point(left_x, current_y),
            undertak_text,
            fontsize=LABEL_FONT_SIZE,
            fontname="hebo",
            color=LABEL_COLOR,
        )
        current_y += LABEL_FONT_SIZE + 1

        # Area value
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
