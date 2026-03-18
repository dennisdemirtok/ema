"""
PDF Result Generator.
Overlays pink on ALL ceiling grid areas, then adds room labels with m².
"""

import fitz
from room_detector import Room, is_h, is_v


ROOM_FILL_COLOR = (1.0, 0.75, 0.80)
ROOM_BORDER_COLOR = (0.80, 0.40, 0.55)
LABEL_FONT_SIZE = 9
LABEL_COLOR = (0.1, 0.1, 0.1)
AREA_COLOR = (0.15, 0.15, 0.4)

GRID_SPACING = 17
GRID_TOL = 3


def _find_grid_lines(wall_lines):
    """Find all horizontal lines that are part of a 17pt ceiling grid pattern."""
    h_lines = []
    for line in wall_lines:
        if not is_h(line):
            continue
        if line.length < 40 or line.length > 500:
            continue
        y = (line.y0 + line.y1) / 2
        xmin = min(line.x0, line.x1)
        xmax = max(line.x0, line.x1)
        h_lines.append((y, xmin, xmax, line.length))

    h_lines.sort()

    # A line is "grid" if it has at least one neighbor at ~17pt with similar length
    grid = []
    for i, (y, x0, x1, l) in enumerate(h_lines):
        for j, (y2, x02, x12, l2) in enumerate(h_lines):
            if i == j:
                continue
            dy = abs(y2 - y)
            if abs(dy - GRID_SPACING) < GRID_TOL:
                if abs(l - l2) < 30 and abs(x0 - x02) < 30:
                    grid.append((y, x0, x1))
                    break

    return grid


def _build_excluded_zones(pdf_data):
    """Find zones that should NOT get pink (Bef rooms, Hiss, Trapphus, title block)."""
    from room_detector import find_room_wall, should_exclude_room
    wall_lines = [l for l in pdf_data.wall_lines if l.length >= 30]

    zones = []
    for label in pdf_data.room_labels:
        if not should_exclude_room(label.text):
            continue
        cx, cy = label.center
        dl = find_room_wall(cx, cy, 'left', wall_lines)
        dr = find_room_wall(cx, cy, 'right', wall_lines)
        du = find_room_wall(cx, cy, 'up', wall_lines)
        dd = find_room_wall(cx, cy, 'down', wall_lines)
        zones.append((cx - dl - 2, cy - du - 2, cx + dr + 2, cy + dd + 2))

    return zones


def _point_in_excluded(y, x0, x1, excluded_zones):
    """Check if a grid line falls inside any excluded zone."""
    mx = (x0 + x1) / 2
    for zx0, zy0, zx1, zy1 in excluded_zones:
        if zx0 <= mx <= zx1 and zy0 <= y <= zy1:
            return True
    return False


def generate_result_pdf(input_path: str, output_path: str, rooms: list,
                        page_num: int = 0) -> str:
    doc = fitz.open(input_path)
    page = doc[page_num]

    # Read all wall lines for grid detection
    import pdf_parser
    pdf_data = pdf_parser.extract_pdf_data(input_path)

    # Find excluded zones (Bef, Hiss, Trapphus)
    excluded = _build_excluded_zones(pdf_data)

    # ── STEP 1: Find grid lines and fill ceiling areas ──
    h_grid = _find_grid_lines(pdf_data.wall_lines)

    fill_shape = page.new_shape()
    half = GRID_SPACING / 2 + 1

    # Filter: only grid lines in the drawing area (not title block)
    # and not in excluded zones
    max_drawing_y = 1010  # Below this is title block

    for y, x0, x1 in h_grid:
        if y > max_drawing_y:
            continue
        if _point_in_excluded(y, x0, x1, excluded):
            continue
        fill_shape.draw_rect(fitz.Rect(x0, y - half, x1, y + half))

    # Vertical grid lines
    v_lines = []
    for line in pdf_data.wall_lines:
        if not is_v(line) or line.length < 40 or line.length > 500:
            continue
        x = (line.x0 + line.x1) / 2
        ymin = min(line.y0, line.y1)
        ymax = max(line.y0, line.y1)
        v_lines.append((x, ymin, ymax, line.length))

    v_lines.sort()
    for i, (x, y0, y1, l) in enumerate(v_lines):
        if y0 > max_drawing_y:
            continue
        is_grid = False
        for j, (x2, y02, y12, l2) in enumerate(v_lines):
            if i == j:
                continue
            if abs(abs(x2 - x) - GRID_SPACING) < GRID_TOL:
                if abs(l - l2) < 30 and abs(y0 - y02) < 30:
                    is_grid = True
                    break
        if is_grid:
            my = (y0 + y1) / 2
            if not _point_in_excluded(my, x - 1, x + 1, excluded):
                fill_shape.draw_rect(fitz.Rect(x - half, y0, x + half, min(y1, max_drawing_y)))

    fill_shape.finish(color=None, fill=ROOM_FILL_COLOR,
                      fill_opacity=0.40, width=0)
    fill_shape.commit()

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
