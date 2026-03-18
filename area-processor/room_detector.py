"""
Room Detection using vector ray-casting with consecutive-spacing grid detection.

For each room label, casts rays in 4 directions.
Detects ceiling grid by finding runs of consecutive ~17pt spacing.
Uses wall-pair detection and boundary analysis to find actual room walls.
"""

from typing import Optional, List, Tuple

from dataclasses import dataclass, field
from pdf_parser import PDFData
from config import MIN_ROOM_AREA_M2, MAX_ROOM_AREA_M2


@dataclass
class Room:
    name: Optional[str] = None
    polygon_pts: list = field(default_factory=list)
    polygon_m: list = field(default_factory=list)
    area_m2: float = 0.0
    centroid_pts: tuple = (0.0, 0.0)
    confidence: float = 0.0
    source: str = "auto"


def is_h(line, tol=2.0):
    return abs(line.y1 - line.y0) < tol

def is_v(line, tol=2.0):
    return abs(line.x1 - line.x0) < tol


def find_all_in_direction(cx, cy, direction, wall_lines, min_dist=3, max_dist=1500):
    """Find ALL wall lines in a direction, sorted by distance."""
    results = []
    for line in wall_lines:
        if direction in ('left', 'right') and is_v(line):
            wall_x = (line.x0 + line.x1) / 2
            y_min = min(line.y0, line.y1)
            y_max = max(line.y0, line.y1)
            if y_min - 10 <= cy <= y_max + 10:
                if direction == 'left' and wall_x < cx:
                    dist = cx - wall_x
                    if min_dist < dist < max_dist:
                        results.append((dist, line.length))
                elif direction == 'right' and wall_x > cx:
                    dist = wall_x - cx
                    if min_dist < dist < max_dist:
                        results.append((dist, line.length))
        elif direction in ('up', 'down') and is_h(line):
            wall_y = (line.y0 + line.y1) / 2
            x_min = min(line.x0, line.x1)
            x_max = max(line.x0, line.x1)
            if x_min - 10 <= cx <= x_max + 10:
                if direction == 'up' and wall_y < cy:
                    dist = cy - wall_y
                    if min_dist < dist < max_dist:
                        results.append((dist, line.length))
                elif direction == 'down' and wall_y > cy:
                    dist = wall_y - cy
                    if min_dist < dist < max_dist:
                        results.append((dist, line.length))
    results.sort(key=lambda x: x[0])
    return results


def find_room_wall(cx, cy, direction, wall_lines, grid_spacing=17, grid_tol=2.5,
                   fallback_wall_lines=None):
    """
    Find the room wall using consecutive-spacing grid detection.

    1. Deduplicate positions, calculate spacings
    2. Find grid runs (2+ consecutive ~17pt spacings)
    3. Check if last grid position is actually a wall (3 rules)
    4. Among non-grid: prefer positions with long-wall pairs
    5. Fallback: first non-grid position
    """
    raw = find_all_in_direction(cx, cy, direction, wall_lines, min_dist=1)
    if not raw:
        return 1500

    # Deduplicate: merge lines within 0.5pt, keep max length
    positions = []  # [(dist, max_length)]
    for dist, length in raw:
        merged = False
        for i, (pd, pl) in enumerate(positions):
            if abs(dist - pd) < 0.5:
                positions[i] = (min(pd, dist), max(pl, length))
                merged = True
                break
        if not merged:
            positions.append((dist, length))

    if len(positions) == 0:
        return 1500
    if len(positions) == 1:
        return positions[0][0]

    # Calculate consecutive spacings
    spacings = []
    for i in range(1, len(positions)):
        spacings.append(positions[i][0] - positions[i - 1][0])

    # Find runs of ~17pt spacings (2+ consecutive)
    is_grid_spacing = [abs(s - grid_spacing) < grid_tol for s in spacings]

    grid_flags = [False] * len(positions)
    grid_runs = []  # [(start_pos_idx, end_pos_idx)]

    run_start = None
    for i in range(len(is_grid_spacing)):
        if is_grid_spacing[i]:
            if run_start is None:
                run_start = i
        else:
            if run_start is not None:
                run_len = i - run_start
                if run_len >= 1:
                    grid_runs.append((run_start, i))  # positions run_start..i
                    for j in range(run_start, i + 1):
                        grid_flags[j] = True
                run_start = None
    if run_start is not None:
        run_len = len(is_grid_spacing) - run_start
        if run_len >= 2:
            grid_runs.append((run_start, len(positions) - 1))
            for j in range(run_start, len(positions)):
                grid_flags[j] = True

    # ── Check if the LAST position of the FIRST grid run is actually a wall ──
    last_grid_idx = grid_runs[0][1] if grid_runs else None

    if last_grid_idx is not None:
        d_last = positions[last_grid_idx][0]
        l_last = positions[last_grid_idx][1]

        # Rule A: tight pair (< 2pt) with non-grid partner → wall double
        # Return the partner (outer face)
        for j in range(len(positions)):
            if j == last_grid_idx or grid_flags[j]:
                continue
            gap = abs(d_last - positions[j][0])
            if 0.1 < gap < 2.0:
                # Wall pair found — return the non-grid partner
                grid_flags[last_grid_idx] = False
                # Prefer the partner (slightly farther = outer face of wall)
                return max(d_last, positions[j][0])

        # Rule B: pair (< 10pt) where partner is a long wall (> 200pt)
        # → structural wall pair with corridor/building wall
        for j in range(len(positions)):
            if j == last_grid_idx:
                continue
            gap = abs(d_last - positions[j][0])
            if 0.5 < gap < 10:
                longer = max(l_last, positions[j][1])
                if longer > 180:
                    grid_flags[last_grid_idx] = False
                    return d_last  # Return the grid position (inner face)

        # Rule C: large gap after last grid position (> 2.5x grid_spacing)
        # → wall at boundary of building/floor
        if last_grid_idx < len(positions) - 1:
            next_gap = positions[last_grid_idx + 1][0] - d_last
            if next_gap > grid_spacing * 2.5:
                # If gap is enormous (>200pt), check for door header segments (29-30pt)
                # just past the grid that are filtered by MIN_WALL_LEN=30
                if next_gap > 200 and fallback_wall_lines is not None:
                    fb_raw = find_all_in_direction(cx, cy, direction,
                                                   fallback_wall_lines, min_dist=1)
                    for fd, fl in fb_raw:
                        # Must be ~1 grid spacing away (the expected next wall position)
                        offset = fd - d_last
                        if grid_spacing * 0.8 < offset < grid_spacing * 1.3 and fl >= 29:
                            return fd
                grid_flags[last_grid_idx] = False
                return d_last
        elif last_grid_idx == len(positions) - 1:
            # It's the very last position — must be the wall
            return d_last

    # ── Find best non-grid position ──
    best_with_long_pair = None  # Position with corridor wall partner (> 200pt)
    best_non_grid = None        # First non-grid position

    # First pass: find first non-grid position
    for i in range(len(positions)):
        if not grid_flags[i]:
            best_non_grid = i
            break

    if best_non_grid is None:
        return positions[-1][0]

    first_non_grid_dist = positions[best_non_grid][0]

    # Search within 30pt of the first non-grid position
    search_limit = first_non_grid_dist + 30
    last_pair_inner = None  # Inner face of the last wall pair in the cluster

    for i in range(len(positions)):
        if grid_flags[i]:
            continue
        if positions[i][0] > search_limit:
            break

        # Check for wall pairs (another position within 0.5-8pt)
        # Both members must be >= 60pt (skip door frames)
        if positions[i][1] < 60:
            continue  # Skip door frames for pair detection
        for j in range(len(positions)):
            if i == j:
                continue
            if positions[j][1] < 40:  # Partner can be slightly shorter
                continue
            gap = abs(positions[i][0] - positions[j][0])
            if 0.5 < gap < 8:
                inner = min(positions[i][0], positions[j][0])
                if last_pair_inner is None or inner > last_pair_inner:
                    last_pair_inner = inner
                break

        # Check for long-wall pair (corridor wall > 200pt within 10pt)
        if positions[i][1] < 60:
            continue
        for j in range(len(positions)):
            if i == j:
                continue
            gap = abs(positions[i][0] - positions[j][0])
            if 0.5 < gap < 10:
                if positions[j][1] > 200:
                    if best_with_long_pair is None:
                        best_with_long_pair = i
                    break

    # Priority 1: Long-wall pair (corridor wall nearby)
    if best_with_long_pair is not None:
        return positions[best_with_long_pair][0]

    # Priority 2: Last wall pair in the nearby cluster
    # BUT only if the first non-grid position doesn't already have a LONG pair partner
    # (if it does, the first non-grid IS the wall, not a soffit)
    first_ng_has_long_pair = False
    if best_non_grid is not None:
        for j in range(len(positions)):
            if j == best_non_grid or grid_flags[j]:
                continue  # Skip self and grid positions
            gap = abs(positions[best_non_grid][0] - positions[j][0])
            if 0.5 < gap < 8 and positions[j][1] >= 60:
                first_ng_has_long_pair = True
                break

    if last_pair_inner is not None and not first_ng_has_long_pair:
        if last_pair_inner > first_non_grid_dist + 3:
            return last_pair_inner

    # Priority 3: First non-grid position
    return first_non_grid_dist

    # All positions are grid — return the last one
    return positions[-1][0]


def find_wall_pairs_nearby(cx, cy, wall_lines, max_search=120, min_len=20):
    """Find structural wall pairs near a point.
    Structural walls in CAD are drawn as double parallel lines (1-8pt apart).
    Returns separate lists for horizontal and vertical wall pairs.
    """
    h_lines = []  # (y_pos, length) - horizontal lines
    v_lines = []  # (x_pos, length) - vertical lines

    for line in wall_lines:
        if line.length < min_len:
            continue
        if is_h(line):
            wall_y = (line.y0 + line.y1) / 2
            if abs(wall_y - cy) < max_search:
                x_min = min(line.x0, line.x1)
                x_max = max(line.x0, line.x1)
                if x_min - 5 <= cx <= x_max + 5:
                    h_lines.append(wall_y)
        elif is_v(line):
            wall_x = (line.x0 + line.x1) / 2
            if abs(wall_x - cx) < max_search:
                y_min = min(line.y0, line.y1)
                y_max = max(line.y0, line.y1)
                if y_min - 5 <= cy <= y_max + 5:
                    v_lines.append(wall_x)

    # Deduplicate and sort
    h_lines = sorted(set(round(y, 1) for y in h_lines))
    v_lines = sorted(set(round(x, 1) for x in v_lines))

    # Find wall pairs (two lines 1-8pt apart)
    def find_pairs(positions):
        pairs = []
        used = set()
        for i in range(len(positions)):
            if i in used:
                continue
            for j in range(i + 1, len(positions)):
                if j in used:
                    continue
                gap = positions[j] - positions[i]
                if 1 < gap < 8:
                    pairs.append((positions[i], positions[j]))
                    used.add(i)
                    used.add(j)
                    break
                if gap >= 8:
                    break
        return pairs

    h_pairs = find_pairs(h_lines)
    v_pairs = find_pairs(v_lines)
    return h_pairs, v_pairs


def find_small_room_rect(cx, cy, wall_lines, pts_to_m2):
    """Find room rectangle for small rooms using wall pair detection."""
    h_pairs, v_pairs = find_wall_pairs_nearby(cx, cy, wall_lines)

    # Find the nearest wall pair above and below
    h_above = [(p[0], p[1]) for p in h_pairs if p[1] < cy]
    h_below = [(p[0], p[1]) for p in h_pairs if p[0] > cy]

    # Find the nearest wall pair left and right
    v_left = [(p[0], p[1]) for p in v_pairs if p[1] < cx]
    v_right = [(p[0], p[1]) for p in v_pairs if p[0] > cx]

    if not h_above or not h_below or not v_left or not v_right:
        return None

    # Use nearest pair in each direction. For ceiling plans, use the face of the
    # wall pair that's closer to the room interior (inner face).
    top = max(p[1] for p in h_above)      # inner face of top wall (lower y)
    bottom = min(p[1] for p in h_below)   # outer face of bottom wall (higher y)
    left = max(p[1] for p in v_left)      # inner face of left wall (right x)
    right = min(p[0] for p in v_right)    # inner face of right wall (left x)

    w = right - left
    h = bottom - top
    if w < 15 or h < 15:
        return None

    area = w * h * pts_to_m2
    if area < 0.5 or area > 50:
        return None

    return (left, top, right, bottom, round(area, 2))


# Room name patterns that indicate SMALL rooms (typically < 10 m²)
import re as _re

# Patterns for rooms that benefit from wall-pair detection (typically small)
_SMALL_ROOM_RE = _re.compile(
    r'(?i)(?:^|\b)(?:wc|städ|hiss|förr[aå]d|klkm|klädkammare|tvätt|teknik|server)(?:\b|$|\d)'
)

def is_small_room_label(text):
    """Check if a label is for a typically small room.
    Matches WC, WC1 but NOT RWC, RWC1.
    """
    text_lower = text.lower().strip()
    # Exclude RWC (it's medium-sized, works better with normal detection)
    if text_lower.startswith('rwc'):
        return False
    return bool(_SMALL_ROOM_RE.search(text_lower))


# Rooms to EXCLUDE from ceiling area calculation
# - "Bef" (befintlig) = existing rooms, no new ceiling
# - Hiss = elevator shaft, no ceiling tiles
# - Trapphus = stairwell, no ceiling tiles
_EXCLUDE_RE = _re.compile(
    r'(?i)(?:^bef\s|^hiss$|^hiss\s|trapphus)'
)

def should_exclude_room(text):
    """Check if a room should be excluded from ceiling area calculation."""
    return bool(_EXCLUDE_RE.search(text.strip()))


def _grid_line_dims(cx, cy, all_wall_lines, search_radius=80):
    """Compute room area from ceiling grid line lengths.

    Grid lines (undertaksplattor 600x600mm) span wall-to-wall within a room.
    The most common line length near the label = the room dimension.
    Returns area in m² or None if no clear grid pattern found.
    """
    from collections import Counter

    h_lens = []
    for line in all_wall_lines:
        if not is_h(line) or line.length < 30 or line.length > 500:
            continue
        y = (line.y0 + line.y1) / 2
        xmin, xmax = min(line.x0, line.x1), max(line.x0, line.x1)
        if abs(y - cy) < search_radius and xmin - 5 <= cx <= xmax + 5:
            h_lens.append(round(line.length, 0))

    v_lens = []
    for line in all_wall_lines:
        if not is_v(line) or line.length < 30 or line.length > 500:
            continue
        x = (line.x0 + line.x1) / 2
        ymin, ymax = min(line.y0, line.y1), max(line.y0, line.y1)
        if abs(x - cx) < search_radius and ymin - 5 <= cy <= ymax + 5:
            v_lens.append(round(line.length, 0))

    if len(h_lens) < 2 or len(v_lens) < 2:
        return None

    h_counter = Counter(h_lens)
    v_counter = Counter(v_lens)

    # Most common length = room dimension. Must have at least 2 occurrences
    h_best, h_count = h_counter.most_common(1)[0]
    v_best, v_count = v_counter.most_common(1)[0]

    if h_count < 2 or v_count < 2:
        return None  # Not enough grid lines to be confident

    return h_best, v_best


def get_grid_room_dims(cx, cy, all_wall_lines, search_radius=80):
    """Wrapper that returns (width_pt, height_pt) or (None, None)."""
    return _grid_line_dims(cx, cy, all_wall_lines, search_radius)


def _get_grid_polygon(cx, cy, all_wall_lines, grid_w, grid_h, search_radius=80):
    """Build polygon from grid line start positions."""
    from statistics import median

    x_starts = []
    for line in all_wall_lines:
        if not is_h(line):
            continue
        y = (line.y0 + line.y1) / 2
        if abs(y - cy) < search_radius and abs(line.length - grid_w) < 5:
            xmin = min(line.x0, line.x1)
            if abs(xmin - cx) < grid_w:  # Line starts near the room
                x_starts.append(xmin)

    y_starts = []
    for line in all_wall_lines:
        if not is_v(line):
            continue
        x = (line.x0 + line.x1) / 2
        if abs(x - cx) < search_radius and abs(line.length - grid_h) < 5:
            ymin = min(line.y0, line.y1)
            if abs(ymin - cy) < grid_h:
                y_starts.append(ymin)

    if not x_starts or not y_starts:
        return None

    x0 = median(x_starts)
    y0 = median(y_starts)
    return [(x0, y0), (x0 + grid_w, y0), (x0 + grid_w, y0 + grid_h), (x0, y0 + grid_h)]


def detect_rooms(pdf_data):
    """Detect rooms using ray-casting with consecutive-spacing grid detection."""
    MIN_WALL_LEN = 30
    MIN_WALL_LEN_FB = 25  # Fallback for door header segments
    wall_lines = [l for l in pdf_data.wall_lines if l.length >= MIN_WALL_LEN]
    wall_lines_fb = [l for l in pdf_data.wall_lines if l.length >= MIN_WALL_LEN_FB]
    pts_to_m = pdf_data.pts_to_m

    print(f"    Wall lines (>={MIN_WALL_LEN}pt): {len(wall_lines)}")
    print(f"    Room labels: {len(pdf_data.room_labels)}")
    print(f"    Scale: 1:{pdf_data.scale}")

    rooms = []
    excluded = 0
    for label in pdf_data.room_labels:
        cx, cy = label.center

        # Skip rooms that don't need ceiling calculation
        if should_exclude_room(label.text):
            excluded += 1
            continue

        if is_small_room_label(label.text):
            # Small rooms: use wall pair detection (structural walls are double lines)
            pts_to_m2 = pts_to_m ** 2
            rect = find_small_room_rect(cx, cy, wall_lines, pts_to_m2)
            if rect is None:
                continue
            left, top, right, bottom, area_m2 = rect
            polygon_pts = [
                (left, top), (right, top), (right, bottom), (left, bottom),
            ]
            rooms.append(Room(
                name=label.text,
                polygon_pts=polygon_pts,
                polygon_m=[(p[0] * pts_to_m, p[1] * pts_to_m) for p in polygon_pts],
                area_m2=round(area_m2, 2),
                centroid_pts=(cx, cy),
                confidence=0.70,
                source="auto"
            ))
            continue

        # PRIMARY: Use grid-line-length for area AND polygon (most accurate)
        grid_w, grid_h = get_grid_room_dims(cx, cy, pdf_data.wall_lines)
        grid_area = None
        grid_polygon = None

        if grid_w and grid_h:
            grid_area = round(grid_w * grid_h * pts_to_m ** 2, 2)
            # Build polygon from grid line positions (where they actually start)
            grid_polygon = _get_grid_polygon(cx, cy, pdf_data.wall_lines, grid_w, grid_h)

        # Ray-casting for fallback
        dl = find_room_wall(cx, cy, 'left', wall_lines, fallback_wall_lines=wall_lines_fb)
        dr = find_room_wall(cx, cy, 'right', wall_lines, fallback_wall_lines=wall_lines_fb)
        du = find_room_wall(cx, cy, 'up', wall_lines, fallback_wall_lines=wall_lines_fb)
        dd = find_room_wall(cx, cy, 'down', wall_lines, fallback_wall_lines=wall_lines_fb)

        ray_area = (dl + dr) * (du + dd) * pts_to_m ** 2
        ray_polygon = [
            (cx - dl, cy - du), (cx + dr, cy - du),
            (cx + dr, cy + dd), (cx - dl, cy + dd),
        ]

        # ALWAYS use ray-casting for the polygon (covers full room extent).
        # Use grid-line-length for AREA when it's available and reasonable
        # (grid is more accurate because it measures wall-to-wall directly).
        polygon_pts = ray_polygon

        if (grid_area
                and MIN_ROOM_AREA_M2 <= grid_area <= MAX_ROOM_AREA_M2
                and ray_area > 0
                and grid_area >= ray_area * 0.5   # Grid shouldn't be much smaller
                and grid_area <= ray_area * 1.1):  # Grid shouldn't be larger
            area_m2 = grid_area
        else:
            area_m2 = ray_area

        # No polygon clipping — ray-cast polygon defines the full ceiling extent

        if area_m2 < MIN_ROOM_AREA_M2 or area_m2 > MAX_ROOM_AREA_M2:
            continue

        rooms.append(Room(
            name=label.text,
            polygon_pts=polygon_pts,
            polygon_m=[(p[0] * pts_to_m, p[1] * pts_to_m) for p in polygon_pts],
            area_m2=round(area_m2, 2),
            centroid_pts=(cx, cy),
            confidence=0.80,
            source="auto"
        ))

    # NOTE: Overlap handling is done in pdf_generator.py (rendering only).
    # Each room keeps its actual measured area — no subtraction here.
    # The PDF renderer clips larger rooms around smaller ones to avoid double-pink.

    # Filter out any rooms with invalid areas
    rooms = [r for r in rooms if r.area_m2 >= MIN_ROOM_AREA_M2]

    print(f"    Rooms detected: {len(rooms)} (excluded {excluded}: Bef/Hiss/Trapphus)")
    return rooms
