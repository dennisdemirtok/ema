"""
PDF Result Generator.
Uses room rectangles + zone background rectangles to produce solid continuous
pink coverage matching the builder's reference.

Strategy (matching the builder's 37-rect approach):
1. Each detected room gets its own rect (no expansion needed - zones fill gaps)
2. One BIG corridor zone rect covers the entire middle band (y~601 to y~870)
   from leftmost room to rightmost non-Pausrum room
3. One Pausrum zone rect covers the entire Pausrum area including ceiling grid
4. All drawn in ONE fitz shape = single fill layer, no double-opacity
5. White masks for excluded areas (Bef, Hiss, Trapphus)
"""

import fitz
from room_detector import Room, should_exclude_room, find_room_wall, is_h, is_v


ROOM_FILL_COLOR = (1.0, 0.75, 0.80)
ROOM_BORDER_COLOR = (0.80, 0.40, 0.55)
LABEL_FONT_SIZE = 9
LABEL_COLOR = (0.1, 0.1, 0.1)
AREA_COLOR = (0.15, 0.15, 0.4)


def _should_mask_room(text):
    """Check if a room should get a white mask in the PDF.

    Only "Bef" (befintlig/existing) rooms get white masks.
    Hiss and Trapphus are NOT masked because:
    - They sit inside the corridor zone background
    - The builder covers them with the corridor zone (no individual masking)
    - Masking Trapphus would incorrectly cut into adjacent ELC rooms
    """
    import re
    return bool(re.match(r'(?i)^bef\s', text.strip()))


def _build_excluded_zones(pdf_data):
    """Build white mask rectangles for rooms that should NOT have pink coverage."""
    wall_lines = [l for l in pdf_data.wall_lines if l.length >= 30]
    zones = []
    for label in pdf_data.room_labels:
        if not _should_mask_room(label.text):
            continue
        cx, cy = label.center
        dl = find_room_wall(cx, cy, 'left', wall_lines)
        dr = find_room_wall(cx, cy, 'right', wall_lines)
        du = find_room_wall(cx, cy, 'up', wall_lines)
        dd = find_room_wall(cx, cy, 'down', wall_lines)
        zones.append((cx - dl, cy - du, cx + dr, cy + dd))
    return zones


def _find_pausrum_right_boundary(pdf_data):
    """Find the right boundary of the Pausrum area by looking for building walls.

    The Pausrum extends rightward past the detected room boundary.
    Look for the building wall at the right edge of the Pausrum zone.
    The builder uses x=2128 which is a structural wall.
    We find it by looking for vertical walls in the range x=2050-2200
    that start near y=480 (top of offices).
    """
    candidates = []
    for line in pdf_data.wall_lines:
        if not is_v(line):
            continue
        x = (line.x0 + line.x1) / 2
        ymin = min(line.y0, line.y1)
        ymax = max(line.y0, line.y1)
        # Must be a structural wall in the Pausrum area (not page border)
        # and start near the top of the office band
        if 2050 < x < 2200 and ymin < 500 and line.length > 100:
            candidates.append(x)
    if candidates:
        return max(candidates)
    return None


def _compute_zone_backgrounds(rooms, pdf_data):
    """Compute zone background rectangles that fill corridors and gaps.

    Matches the builder's approach:
      - [~286,~601]->[~1916,~870] = ONE big corridor/middle zone
      - [~1713,~480]->[~2128,~818] = ONE big Pausrum zone
    """
    zones = []

    # Classify rooms into bands
    top_band = []      # top row offices only (y0 ~ 470-490, y1 ~ 597)
    middle_band = []   # middle rooms including corridors
    bottom_band = []   # bottom studios (y0 > 860)
    pausrum = None

    for room in rooms:
        if len(room.polygon_pts) < 3:
            continue
        p = room.polygon_pts
        x0, y0 = p[0]
        x1, y1 = p[2]

        if room.name and 'pausrum' in room.name.lower():
            pausrum = room
            continue

        # Top band: offices with y1 ~ 597 (NOT corridors that extend lower)
        if y0 < 500 and y1 < 610:
            top_band.append((x0, y0, x1, y1))
        elif y0 >= 855:
            bottom_band.append((x0, y0, x1, y1))
        else:
            middle_band.append((x0, y0, x1, y1))

    # ── Zone 1: Big corridor/middle zone ──
    # Spans from just below top-band offices to just above bottom-band studios,
    # across the full width from leftmost to rightmost room (excluding Pausrum).
    # Builder reference: [286,601]->[1916,870]
    all_non_pausrum = top_band + middle_band + bottom_band
    if all_non_pausrum:
        left_x = min(r[0] for r in all_non_pausrum)
        right_x = max(r[2] for r in all_non_pausrum)

        # Top of zone: a few points below bottom of top-band offices
        # Builder uses y=601, offices end at y=597. Gap = ~4pt (wall thickness)
        if top_band:
            zone_top = max(r[3] for r in top_band) + 4  # 597 + 4 = ~601
        else:
            zone_top = 601

        # Bottom of zone: just below the lowest middle-band room but above studios
        # Builder uses y=870, studios start at y=874. Gap = ~4pt
        if bottom_band:
            zone_bottom = min(r[1] for r in bottom_band) - 4  # 874 - 4 = ~870
        else:
            zone_bottom = 870

        zones.append((left_x, zone_top, right_x, zone_bottom))

    # ── Zone 2: Pausrum zone ──
    # Covers from Pausrum left edge all the way to building right wall,
    # from top of Pausrum down to where middle-band rooms end (~y=818).
    # The builder draws [1713,480]->[2128,818].
    if pausrum and len(pausrum.polygon_pts) >= 3:
        p = pausrum.polygon_pts
        px0, py0 = p[0]
        px1, py1 = p[2]

        # Find actual building right boundary (further right than detected room)
        right_boundary = _find_pausrum_right_boundary(pdf_data)
        if right_boundary and right_boundary > px1:
            px1 = right_boundary

        # The Pausrum zone bottom should match the bottom of rooms
        # that are fully inside the Pausrum x-range (x0 >= 1700).
        # This gives us KÖK (y1=818) but excludes ELC and Korridor
        # which extend further down and are covered by the corridor zone.
        rooms_in_pausrum = [r for r in middle_band
                            if r[0] >= 1700 and r[2] <= px1 + 50]
        if rooms_in_pausrum:
            py1_extended = max(r[3] for r in rooms_in_pausrum)
        else:
            py1_extended = py1

        zones.append((px0, py0, px1, py1_extended))

    return zones


def generate_result_pdf(input_path: str, output_path: str, rooms: list,
                        page_num: int = 0) -> str:
    doc = fitz.open(input_path)
    page = doc[page_num]

    if not rooms:
        doc.save(output_path)
        doc.close()
        return output_path

    # ── Build excluded zones ──
    import pdf_parser as _pp
    pdf_data = _pp.extract_pdf_data(input_path)
    excluded = _build_excluded_zones(pdf_data)

    # ── Compute zone backgrounds ──
    zone_bgs = _compute_zone_backgrounds(rooms, pdf_data)

    # ── Draw everything in ONE shape (single fill layer) ──
    fill = page.new_shape()

    # 1. Zone backgrounds (large covering rects for corridors/gaps)
    for x0, y0, x1, y1 in zone_bgs:
        fill.draw_rect(fitz.Rect(x0, y0, x1, y1))

    # 2. Individual room rects
    for room in rooms:
        if len(room.polygon_pts) < 3:
            continue
        p = room.polygon_pts
        x0, y0 = p[0]
        x1, y1 = p[2]
        fill.draw_rect(fitz.Rect(x0, y0, x1, y1))

    # Single finish = single fill layer, no double-opacity
    fill.finish(color=None, fill=ROOM_FILL_COLOR, fill_opacity=0.40, width=0)
    fill.commit()

    # ── White masks for excluded areas ──
    # Draw each mask in its own shape to ensure proper coverage
    for x0, y0, x1, y1 in excluded:
        mask = page.new_shape()
        mask.draw_rect(fitz.Rect(x0 - 1, y0 - 1, x1 + 1, y1 + 1))
        mask.finish(color=None, fill=(1, 1, 1), fill_opacity=1.0, width=0)
        mask.commit()

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
