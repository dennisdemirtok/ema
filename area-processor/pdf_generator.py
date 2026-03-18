"""
PDF Result Generator.
Draws pink ceiling coverage using exactly the same approach as the builder:
- Individual room rectangles
- ONE big corridor zone covering entire middle section
- ONE big Pausrum zone covering right section
All in a single shape = no double-opacity.
"""

import fitz
from room_detector import Room


ROOM_FILL_COLOR = (1.0, 0.75, 0.80)
ROOM_BORDER_COLOR = (0.80, 0.40, 0.55)
LABEL_FONT_SIZE = 9
LABEL_COLOR = (0.1, 0.1, 0.1)
AREA_COLOR = (0.15, 0.15, 0.4)


def generate_result_pdf(input_path: str, output_path: str, rooms: list,
                        page_num: int = 0) -> str:
    doc = fitz.open(input_path)
    page = doc[page_num]

    if not rooms:
        doc.save(output_path)
        doc.close()
        return output_path

    # ── Classify rooms into rows ──
    top_rooms = []     # y_center < 610 (top office row)
    mid_rooms = []     # 610 <= y_center < 875 (middle section)
    bot_rooms = []     # y_center >= 875 (bottom studios)

    for r in rooms:
        cy = r.centroid_pts[1]
        if cy < 610:
            top_rooms.append(r)
        elif cy < 875:
            mid_rooms.append(r)
        else:
            bot_rooms.append(r)

    # ── Compute the 2 big zone rects (like the builder does) ──
    # These fill corridors and gaps between individual rooms.

    # Zone 1: Corridor/middle - spans full width, from below top offices to above studios
    # Builder: [286,601]->[1916,870]
    all_rooms = top_rooms + mid_rooms + bot_rooms
    if all_rooms:
        global_x0 = min(r.polygon_pts[0][0] for r in all_rooms)
        global_x1 = max(r.polygon_pts[2][0] for r in all_rooms if
                        'pausrum' not in (r.name or '').lower())

        top_y1 = max(r.polygon_pts[2][1] for r in top_rooms) if top_rooms else 597
        bot_y0 = min(r.polygon_pts[0][1] for r in bot_rooms) if bot_rooms else 874

        corridor_zone = (global_x0, top_y1 + 4, global_x1, bot_y0 - 4)
    else:
        corridor_zone = None

    # Zone 2: Pausrum - find Pausrum room and extend to building wall
    pausrum_zone = None
    for r in rooms:
        if r.name and 'pausrum' in r.name.lower():
            p = r.polygon_pts
            # Extend right edge to building wall (find furthest structural wall > x=2050)
            right_x = p[2][0]
            import pdf_parser as _pp
            from room_detector import is_v
            pdf_data = _pp.extract_pdf_data(input_path)
            for line in pdf_data.wall_lines:
                if not is_v(line):
                    continue
                x = (line.x0 + line.x1) / 2
                ymin = min(line.y0, line.y1)
                if 2050 < x < 2200 and ymin < 500 and line.length > 100:
                    right_x = max(right_x, x)

            # Extend bottom to match KÖK/Skrivare bottom (~818)
            bottom_y = p[2][1]
            for mr in mid_rooms:
                mp = mr.polygon_pts
                if mp[0][0] >= 1700:  # rooms in Pausrum x-range
                    bottom_y = max(bottom_y, mp[2][1])

            pausrum_zone = (p[0][0], p[0][1], right_x, bottom_y)
            break

    # ── DRAW: All rects in ONE shape ──
    fill = page.new_shape()

    # 1. Zone backgrounds
    if corridor_zone:
        fill.draw_rect(fitz.Rect(*corridor_zone))
    if pausrum_zone:
        fill.draw_rect(fitz.Rect(*pausrum_zone))

    # 2. All individual room rects
    for room in rooms:
        if len(room.polygon_pts) < 3:
            continue
        p = room.polygon_pts
        fill.draw_rect(fitz.Rect(p[0][0], p[0][1], p[2][0], p[2][1]))

    # Single finish = ONE layer, no double-opacity
    fill.finish(color=None, fill=ROOM_FILL_COLOR, fill_opacity=0.40, width=0)
    fill.commit()

    # ── WHITE MASKS: only for "Bef" rooms ──
    import re
    if 'pdf_data' not in dir():
        import pdf_parser as _pp
        pdf_data = _pp.extract_pdf_data(input_path)

    from room_detector import find_room_wall
    wall_lines = [l for l in pdf_data.wall_lines if l.length >= 30]

    for label in pdf_data.room_labels:
        text = label.text.strip()
        if not re.match(r'(?i)^bef\s', text):
            continue
        cx, cy = label.center
        dl = find_room_wall(cx, cy, 'left', wall_lines)
        dr = find_room_wall(cx, cy, 'right', wall_lines)
        du = find_room_wall(cx, cy, 'up', wall_lines)
        dd = find_room_wall(cx, cy, 'down', wall_lines)
        mask = page.new_shape()
        mask.draw_rect(fitz.Rect(cx-dl, cy-du, cx+dr, cy+dd))
        mask.finish(color=None, fill=(1,1,1), fill_opacity=1.0, width=0)
        mask.commit()

    # ── ROOM BORDERS ──
    border = page.new_shape()
    for room in rooms:
        if len(room.polygon_pts) < 3:
            continue
        p = room.polygon_pts
        border.draw_rect(fitz.Rect(p[0][0], p[0][1], p[2][0], p[2][1]))
    border.finish(color=ROOM_BORDER_COLOR, fill=None, width=0.4, stroke_opacity=0.3)
    border.commit()

    # ── LABELS ──
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
