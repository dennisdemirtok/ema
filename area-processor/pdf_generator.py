"""
PDF Result Generator.
Detects ceiling grid areas and fills them with pink. Adds room labels.
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


def _find_grid_h_lines(wall_lines):
    """Find horizontal lines that are part of a ceiling grid pattern."""
    h_lines = []
    for line in wall_lines:
        if not is_h(line) or line.length < 40 or line.length > 500:
            continue
        y = (line.y0 + line.y1) / 2
        h_lines.append((y, min(line.x0, line.x1), max(line.x0, line.x1), line.length))
    h_lines.sort()

    grid = []
    for i, (y, x0, x1, l) in enumerate(h_lines):
        for j, (y2, x02, x12, l2) in enumerate(h_lines):
            if i == j:
                continue
            if abs(abs(y2 - y) - GRID_SPACING) < GRID_TOL:
                if abs(l - l2) < 30 and abs(x0 - x02) < 30:
                    grid.append((y, x0, x1))
                    break
    return grid


def _build_excluded_zones(pdf_data):
    """Find zones that should NOT get pink."""
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
        zones.append((cx - dl - 3, cy - du - 3, cx + dr + 3, cy + dd + 3))
    return zones


def _point_in_zone(y, x, zones):
    for zx0, zy0, zx1, zy1 in zones:
        if zx0 <= x <= zx1 and zy0 <= y <= zy1:
            return True
    return False


def _compute_grid_regions(grid_lines, excluded_zones, max_y=1010):
    """Merge grid lines into solid rectangular regions.

    Groups grid lines with similar x-range, then for each group
    creates a rectangle from min_y to max_y spanning the x-range.
    """
    # Filter
    filtered = []
    for y, x0, x1 in grid_lines:
        if y > max_y:
            continue
        mx = (x0 + x1) / 2
        if _point_in_zone(y, mx, excluded_zones):
            continue
        filtered.append((y, x0, x1))

    if not filtered:
        return []

    # Group by similar x-range: lines within 20pt of each other in x
    # belong to the same room/region
    from collections import defaultdict

    # Round x0 and x1 to nearest 15pt to group similar lines
    groups = defaultdict(list)
    for y, x0, x1 in filtered:
        key = (round(x0 / 15) * 15, round(x1 / 15) * 15)
        groups[key].append((y, x0, x1))

    # For each group, compute the bounding rectangle
    rects = []
    for (kx0, kx1), lines in groups.items():
        y_min = min(y for y, _, _ in lines) - GRID_SPACING / 2
        y_max = max(y for y, _, _ in lines) + GRID_SPACING / 2
        x_min = min(x0 for _, x0, _ in lines)
        x_max = max(x1 for _, _, x1 in lines)
        # Only include if it has multiple lines (actual grid, not lone line)
        if len(lines) >= 2:
            rects.append((x_min, y_min, x_max, y_max))

    # Merge overlapping rectangles
    changed = True
    while changed:
        changed = False
        merged = []
        used = set()
        for i in range(len(rects)):
            if i in used:
                continue
            r = list(rects[i])
            for j in range(i + 1, len(rects)):
                if j in used:
                    continue
                s = rects[j]
                # Check overlap with 5pt tolerance
                if (r[0] - 5 <= s[2] and s[0] - 5 <= r[2] and
                        r[1] - 5 <= s[3] and s[1] - 5 <= r[3]):
                    r[0] = min(r[0], s[0])
                    r[1] = min(r[1], s[1])
                    r[2] = max(r[2], s[2])
                    r[3] = max(r[3], s[3])
                    used.add(j)
                    changed = True
            merged.append(tuple(r))
            used.add(i)
        rects = merged

    return rects


def generate_result_pdf(input_path: str, output_path: str, rooms: list,
                        page_num: int = 0) -> str:
    doc = fitz.open(input_path)
    page = doc[page_num]

    import pdf_parser
    pdf_data = pdf_parser.extract_pdf_data(input_path)

    excluded = _build_excluded_zones(pdf_data)
    h_grid = _find_grid_h_lines(pdf_data.wall_lines)

    # ── STEP 1: Compute solid grid regions and draw them ──
    regions = _compute_grid_regions(h_grid, excluded)

    fill_shape = page.new_shape()
    for x0, y0, x1, y1 in regions:
        fill_shape.draw_rect(fitz.Rect(x0, y0, x1, y1))
    fill_shape.finish(color=None, fill=ROOM_FILL_COLOR,
                      fill_opacity=0.40, width=0)
    fill_shape.commit()

    # ── STEP 2: Room borders ──
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
