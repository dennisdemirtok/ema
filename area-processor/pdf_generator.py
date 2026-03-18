"""
PDF Result Generator.
Fills ceiling areas with pink using room polygons + zone backgrounds,
all drawn in a SINGLE shape to avoid double-opacity.
Masks excluded zones (Bef, Hiss, Trapphus) with white.
"""

import fitz
from room_detector import Room, should_exclude_room, find_room_wall, is_h, is_v


ROOM_FILL_COLOR = (1.0, 0.75, 0.80)
ROOM_BORDER_COLOR = (0.80, 0.40, 0.55)
LABEL_FONT_SIZE = 9
LABEL_COLOR = (0.1, 0.1, 0.1)
AREA_COLOR = (0.15, 0.15, 0.4)
EXPAND = 4  # Expand each room rect to fill wall gaps


def generate_result_pdf(input_path: str, output_path: str, rooms: list,
                        page_num: int = 0) -> str:
    doc = fitz.open(input_path)
    page = doc[page_num]

    if not rooms:
        doc.save(output_path)
        doc.close()
        return output_path

    # ── Collect ALL rectangles to fill (rooms + zone backgrounds) ──
    all_rects = []

    # Add each room rectangle (expanded to fill wall gaps)
    for room in rooms:
        if len(room.polygon_pts) < 3:
            continue
        p = room.polygon_pts
        all_rects.append(fitz.Rect(
            p[0][0] - EXPAND, p[0][1] - EXPAND,
            p[2][0] + EXPAND, p[2][1] + EXPAND
        ))

    # Add zone backgrounds to fill corridor/gap areas between rooms
    # Group rooms by band (top offices, middle, studios)
    band1 = [r for r in rooms if r.centroid_pts[1] < 610]  # top offices
    band2 = [r for r in rooms if 610 <= r.centroid_pts[1] < 875]  # middle
    band3 = [r for r in rooms if r.centroid_pts[1] >= 875]  # studios

    for band in [band1, band2, band3]:
        if len(band) < 2:
            continue
        x0 = min(r.polygon_pts[0][0] for r in band) - EXPAND
        y0 = min(r.polygon_pts[0][1] for r in band) - EXPAND
        x1 = max(r.polygon_pts[2][0] for r in band) + EXPAND
        y1 = max(r.polygon_pts[2][1] for r in band) + EXPAND
        all_rects.append(fitz.Rect(x0, y0, x1, y1))

    # Connect band1 and band2 (they share the corridor zone)
    if band1 and band2:
        x0 = min(
            min(r.polygon_pts[0][0] for r in band1),
            min(r.polygon_pts[0][0] for r in band2)
        ) - EXPAND
        x1 = max(
            max(r.polygon_pts[2][0] for r in band1),
            max(r.polygon_pts[2][0] for r in band2)
        ) + EXPAND
        y0 = min(r.polygon_pts[0][1] for r in band1) - EXPAND
        y1 = max(r.polygon_pts[2][1] for r in band2) + EXPAND
        all_rects.append(fitz.Rect(x0, y0, x1, y1))

    # ── STEP 1: Draw ALL rects in ONE shape (no double-opacity!) ──
    fill = page.new_shape()
    for rect in all_rects:
        fill.draw_rect(rect)
    fill.finish(color=None, fill=ROOM_FILL_COLOR, fill_opacity=0.40, width=0)
    fill.commit()

    # ── STEP 2: Mask excluded areas with white ──
    import pdf_parser as _pp
    pdf_data = _pp.extract_pdf_data(input_path)
    wall_lines = [l for l in pdf_data.wall_lines if l.length >= 30]

    mask = page.new_shape()
    for label in pdf_data.room_labels:
        if not should_exclude_room(label.text):
            continue
        cx, cy = label.center
        dl = find_room_wall(cx, cy, 'left', wall_lines)
        dr = find_room_wall(cx, cy, 'right', wall_lines)
        du = find_room_wall(cx, cy, 'up', wall_lines)
        dd = find_room_wall(cx, cy, 'down', wall_lines)
        mask.draw_rect(fitz.Rect(cx - dl + 2, cy - du + 2,
                                  cx + dr - 2, cy + dd - 2))
    mask.finish(color=None, fill=(1, 1, 1), fill_opacity=1.0, width=0)
    mask.commit()

    # ── STEP 3: Room borders ──
    border = page.new_shape()
    for room in rooms:
        if len(room.polygon_pts) < 3:
            continue
        p = room.polygon_pts
        border.draw_rect(fitz.Rect(p[0][0], p[0][1], p[2][0], p[2][1]))
    border.finish(color=ROOM_BORDER_COLOR, fill=None, width=0.4, stroke_opacity=0.3)
    border.commit()

    # ── STEP 4: Labels ──
    for room in rooms:
        if len(room.polygon_pts) < 3:
            continue
        cx, cy = room.centroid_pts
        area_str = f"{room.area_m2:.2f}".replace(".", ",")
        name_text = room.name or ""
        lines_count = 3 if name_text else 2
        max_text = max(len("Undertak"), len(f"{area_str} m²"),
                       len(name_text) if name_text else 0)
        tw = max(max_text * LABEL_FONT_SIZE * 0.52, 50)
        th = LABEL_FONT_SIZE * (lines_count + 0.8)
        lr = fitz.Rect(cx - tw/2, cy - th/2, cx + tw/2, cy + th/2)

        bg = page.new_shape()
        bg.draw_rect(lr)
        bg.finish(color=(0.7,0.7,0.7), fill=(1,1,1), fill_opacity=0.92, width=0.3)
        bg.commit()

        lx = cx - tw/2 + 3
        ly = cy - th/2 + LABEL_FONT_SIZE + 1
        if name_text:
            page.insert_text(fitz.Point(lx, ly), name_text,
                             fontsize=LABEL_FONT_SIZE-1, fontname="helv", color=LABEL_COLOR)
            ly += LABEL_FONT_SIZE + 1
        page.insert_text(fitz.Point(lx, ly), "Undertak",
                         fontsize=LABEL_FONT_SIZE, fontname="hebo", color=LABEL_COLOR)
        ly += LABEL_FONT_SIZE + 1
        page.insert_text(fitz.Point(lx, ly), f"{area_str} m²",
                         fontsize=LABEL_FONT_SIZE, fontname="helv", color=AREA_COLOR)

    doc.save(output_path)
    doc.close()
    return output_path
