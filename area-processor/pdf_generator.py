"""
PDF Result Generator.
Fills ceiling areas with pink, masks excluded zones, adds room labels.
"""

import fitz
from room_detector import Room, is_h, is_v


ROOM_FILL_COLOR = (1.0, 0.75, 0.80)
ROOM_BORDER_COLOR = (0.80, 0.40, 0.55)
LABEL_FONT_SIZE = 9
LABEL_COLOR = (0.1, 0.1, 0.1)
AREA_COLOR = (0.15, 0.15, 0.4)
PAD = 4  # padding around zones


def generate_result_pdf(input_path: str, output_path: str, rooms: list,
                        page_num: int = 0) -> str:
    doc = fitz.open(input_path)
    page = doc[page_num]

    if not rooms:
        doc.save(output_path)
        doc.close()
        return output_path

    # ── Compute ceiling zones from room positions ──
    # Group rooms by centroid Y into 3 bands
    band1, band2, band3 = [], [], []
    for r in rooms:
        cy = r.centroid_pts[1]
        if cy < 610:
            band1.append(r)
        elif cy < 875:
            band2.append(r)
        else:
            band3.append(r)

    # Compute zone rectangles (bounding box of each band)
    zones = []
    for band in [band1, band2, band3]:
        if not band:
            continue
        x0 = min(r.polygon_pts[0][0] for r in band) - PAD
        y0 = min(r.polygon_pts[0][1] for r in band) - PAD
        x1 = max(r.polygon_pts[2][0] for r in band) + PAD
        y1 = max(r.polygon_pts[2][1] for r in band) + PAD
        zones.append((x0, y0, x1, y1))

    # ── STEP 1: Draw pink zone backgrounds ──
    fill = page.new_shape()
    for z in zones:
        fill.draw_rect(fitz.Rect(z[0], z[1], z[2], z[3]))
    fill.finish(color=None, fill=ROOM_FILL_COLOR, fill_opacity=0.40, width=0)
    fill.commit()

    # ── STEP 2: Mask excluded areas with white ──
    # Find Bef/Hiss/Trapphus zones and cover them with white
    import pdf_parser
    pdf_data = pdf_parser.extract_pdf_data(input_path)

    from room_detector import find_room_wall, should_exclude_room
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
        # White rectangle to cover the pink
        mask.draw_rect(fitz.Rect(cx - dl + 1, cy - du + 1,
                                  cx + dr - 1, cy + dd - 1))
    mask.finish(color=None, fill=(1, 1, 1), fill_opacity=1.0, width=0)
    mask.commit()

    # ── STEP 3: Room borders ──
    border = page.new_shape()
    for room in rooms:
        if len(room.polygon_pts) < 3:
            continue
        p = room.polygon_pts
        border.draw_rect(fitz.Rect(p[0][0], p[0][1], p[2][0], p[2][1]))
    border.finish(color=ROOM_BORDER_COLOR, fill=None, width=0.4, stroke_opacity=0.35)
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
