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


def find_room_wall(cx, cy, direction, wall_lines, grid_spacing=17, grid_tol=2.5):
    """
    Find the room wall using consecutive-spacing grid detection.

    1. Deduplicate positions, calculate spacings
    2. Find grid runs (2+ consecutive ~17pt spacings)
    3. Check if last grid position is actually a wall (3 rules)
    4. Among non-grid: prefer positions with long-wall pairs
    5. Fallback: first non-grid position
    """
    raw = find_all_in_direction(cx, cy, direction, wall_lines, min_dist=3)
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
                if run_len >= 2:
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
                if longer > 200:
                    grid_flags[last_grid_idx] = False
                    return d_last  # Return the grid position (inner face)

        # Rule C: large gap after last grid position (> 2.5x grid_spacing)
        # → wall at boundary of building/floor
        if last_grid_idx < len(positions) - 1:
            next_gap = positions[last_grid_idx + 1][0] - d_last
            if next_gap > grid_spacing * 2.5:
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
    if last_pair_inner is not None and last_pair_inner > first_non_grid_dist + 3:
        return last_pair_inner

    # Priority 3: First non-grid position
    return first_non_grid_dist

    # All positions are grid — return the last one
    return positions[-1][0]


def detect_rooms(pdf_data):
    """Detect rooms using ray-casting with consecutive-spacing grid detection."""
    MIN_WALL_LEN = 30
    wall_lines = [l for l in pdf_data.wall_lines if l.length >= MIN_WALL_LEN]
    pts_to_m = pdf_data.pts_to_m

    print(f"    Wall lines (>={MIN_WALL_LEN}pt): {len(wall_lines)}")
    print(f"    Room labels: {len(pdf_data.room_labels)}")
    print(f"    Scale: 1:{pdf_data.scale}")

    rooms = []
    for label in pdf_data.room_labels:
        cx, cy = label.center

        dl = find_room_wall(cx, cy, 'left', wall_lines)
        dr = find_room_wall(cx, cy, 'right', wall_lines)
        du = find_room_wall(cx, cy, 'up', wall_lines)
        dd = find_room_wall(cx, cy, 'down', wall_lines)

        width_m = (dl + dr) * pts_to_m
        height_m = (du + dd) * pts_to_m
        area_m2 = width_m * height_m

        if area_m2 < MIN_ROOM_AREA_M2 or area_m2 > MAX_ROOM_AREA_M2:
            continue

        polygon_pts = [
            (cx - dl, cy - du),
            (cx + dr, cy - du),
            (cx + dr, cy + dd),
            (cx - dl, cy + dd),
        ]

        rooms.append(Room(
            name=label.text,
            polygon_pts=polygon_pts,
            polygon_m=[(p[0] * pts_to_m, p[1] * pts_to_m) for p in polygon_pts],
            area_m2=round(area_m2, 2),
            centroid_pts=(cx, cy),
            confidence=0.80,
            source="auto"
        ))

    print(f"    Rooms detected: {len(rooms)}")
    return rooms
