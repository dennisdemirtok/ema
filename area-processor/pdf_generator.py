"""
PDF Result Generator.
Takes the original PDF and overlays pink/rosa room polygons with "Undertak X,XX m²" labels.
Styled to match professional Swedish ceiling plan (undertaksritning) output.
"""

import fitz  # PyMuPDF
from room_detector import Room


ROOM_FILL_COLOR = (1.0, 0.75, 0.80)
ROOM_BORDER_COLOR = (0.80, 0.40, 0.55)
LABEL_FONT_SIZE = 9
LABEL_COLOR = (0.1, 0.1, 0.1)
AREA_COLOR = (0.15, 0.15, 0.4)
EXPAND = 4


def generate_result_pdf(input_path: str, output_path: str, rooms: list,
                        page_num: int = 0) -> str:
    doc = fitz.open(input_path)
    page = doc[page_num]

    # ── STEP 0: Detect and draw ceiling ZONE backgrounds ──
    # Like the builder's reference: large background rectangles that cover
    # entire ceiling areas including corridors and spaces between rooms.
    if rooms:
        # Group rooms by centroid Y into bands
        # Band 1: top offices (centroid y < 600)
        # Band 2: middle zone (600 <= centroid y < 870)
        # Band 3: bottom studios (centroid y >= 870)
        bands = [[], [], []]
        for r in rooms:
            cy = r.centroid_pts[1]
            if cy < 600:
                bands[0].append(r)
            elif cy < 870:
                bands[1].append(r)
            else:
                bands[2].append(r)

        zone_shape = page.new_shape()
        for group in bands:
            if not group:
                continue
            # Zone = bounding box of all room polygons in this band
            zx0 = min(r.polygon_pts[0][0] for r in group) - EXPAND
            zy0 = min(r.polygon_pts[0][1] for r in group) - EXPAND
            zx1 = max(r.polygon_pts[2][0] for r in group) + EXPAND
            zy1 = max(r.polygon_pts[2][1] for r in group) + EXPAND
            zone_shape.draw_rect(fitz.Rect(zx0, zy0, zx1, zy1))

        zone_shape.finish(color=None, fill=ROOM_FILL_COLOR,
                          fill_opacity=0.35, width=0)
        zone_shape.commit()

    # ── STEP 1: Draw ALL room fills expanded, each in its OWN shape ──
    # Draw largest first (background), smallest last (on top).
    # Each shape is separate so we get consistent opacity everywhere.
    rooms_sorted = sorted(rooms, key=lambda r: -r.area_m2)

    for room in rooms_sorted:
        if len(room.polygon_pts) < 3:
            continue
        p = room.polygon_pts
        rx0, ry0 = p[0]
        rx1, ry1 = p[2]
        rect = fitz.Rect(rx0 - EXPAND, ry0 - EXPAND,
                         rx1 + EXPAND, ry1 + EXPAND)
        shape = page.new_shape()
        shape.draw_rect(rect)
        shape.finish(color=None, fill=ROOM_FILL_COLOR,
                     fill_opacity=0.40, width=0)
        shape.commit()

    # ── STEP 2: Draw room borders ──
    border_shape = page.new_shape()
    for room in rooms:
        if len(room.polygon_pts) < 3:
            continue
        p = room.polygon_pts
        border_shape.draw_rect(fitz.Rect(p[0][0], p[0][1], p[2][0], p[2][1]))
    border_shape.finish(color=ROOM_BORDER_COLOR, fill=None,
                        width=0.4, stroke_opacity=0.35)
    border_shape.commit()

    # ── STEP 3: Labels ──
    for room in rooms:
        if len(room.polygon_pts) < 3:
            continue

        cx, cy = room.centroid_pts
        area_str = f"{room.area_m2:.2f}".replace(".", ",")
        name_text = room.name or ""

        lines_count = 3 if name_text else 2
        max_text = max(len("Undertak"), len(f"{area_str} m²"),
                       len(name_text) if name_text else 0)
        text_width = max(max_text * LABEL_FONT_SIZE * 0.52, 50)
        text_height = LABEL_FONT_SIZE * (lines_count + 0.8)

        label_rect = fitz.Rect(
            cx - text_width / 2, cy - text_height / 2,
            cx + text_width / 2, cy + text_height / 2,
        )

        bg = page.new_shape()
        bg.draw_rect(label_rect)
        bg.finish(color=(0.7, 0.7, 0.7), fill=(1, 1, 1),
                  fill_opacity=0.92, width=0.3)
        bg.commit()

        left_x = cx - text_width / 2 + 3
        cur_y = cy - text_height / 2 + LABEL_FONT_SIZE + 1

        if name_text:
            page.insert_text(fitz.Point(left_x, cur_y), name_text,
                             fontsize=LABEL_FONT_SIZE - 1, fontname="helv",
                             color=LABEL_COLOR)
            cur_y += LABEL_FONT_SIZE + 1

        page.insert_text(fitz.Point(left_x, cur_y), "Undertak",
                         fontsize=LABEL_FONT_SIZE, fontname="hebo",
                         color=LABEL_COLOR)
        cur_y += LABEL_FONT_SIZE + 1

        page.insert_text(fitz.Point(left_x, cur_y), f"{area_str} m²",
                         fontsize=LABEL_FONT_SIZE, fontname="helv",
                         color=AREA_COLOR)

    doc.save(output_path)
    doc.close()
    return output_path
