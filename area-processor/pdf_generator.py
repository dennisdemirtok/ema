"""
PDF Result Generator.
Draws pink rectangles ONLY for measured rooms — nothing else.
Each detected room with ceiling tiles gets its own pink rect + label.
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

    # ── Post-process: merge Korridor rooms into one continuous rect ──
    # The corridor is detected as 2 strips but should be one continuous area.
    korridor_rooms = [r for r in rooms if r.name and 'korridor' in r.name.lower()]
    if len(korridor_rooms) >= 2:
        # Merge all korridor rects into bounding box
        kx0 = min(r.polygon_pts[0][0] for r in korridor_rooms)
        ky0 = min(r.polygon_pts[0][1] for r in korridor_rooms)
        kx1 = max(r.polygon_pts[2][0] for r in korridor_rooms)
        ky1 = max(r.polygon_pts[2][1] for r in korridor_rooms)
        # Update first korridor room to cover the merged area
        total_area = round((kx1 - kx0) * (ky1 - ky0) * 0.0352778 ** 2, 2)
        korridor_rooms[0].polygon_pts = [(kx0, ky0), (kx1, ky0), (kx1, ky1), (kx0, ky1)]
        korridor_rooms[0].area_m2 = total_area
        # Remove the extra korridor rooms
        for kr in korridor_rooms[1:]:
            rooms.remove(kr)

    # ── Draw ONLY the measured room rectangles ──
    # ONE shape = single fill layer, no double-opacity
    fill = page.new_shape()
    for room in rooms:
        if len(room.polygon_pts) < 3:
            continue
        p = room.polygon_pts
        fill.draw_rect(fitz.Rect(p[0][0], p[0][1], p[2][0], p[2][1]))
    fill.finish(color=None, fill=ROOM_FILL_COLOR, fill_opacity=0.40, width=0)
    fill.commit()

    # ── Room borders ──
    border = page.new_shape()
    for room in rooms:
        if len(room.polygon_pts) < 3:
            continue
        p = room.polygon_pts
        border.draw_rect(fitz.Rect(p[0][0], p[0][1], p[2][0], p[2][1]))
    border.finish(color=ROOM_BORDER_COLOR, fill=None, width=0.4, stroke_opacity=0.3)
    border.commit()

    # ── Labels ──
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
