"""
Room Detection using vector ray-casting with consecutive-spacing grid detection.

For each room label, casts rays in 4 directions.
Detects ceiling grid by finding runs of consecutive ~17pt spacing.
The first line after the grid run is the room wall.
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


def find_room_wall(cx, cy, direction, wall_lines, grid_spacing=17, grid_tol=3.5):
    """
    Find the room wall using consecutive-spacing grid detection.

    Strategy:
    1. Get all lines sorted by distance, deduplicate positions
    2. Calculate consecutive spacings between positions
    3. Find the longest run of ~17pt spacings = grid
    4. The first line after the grid run is the room wall
    """
    raw = find_all_in_direction(cx, cy, direction, wall_lines, min_dist=3)
    if not raw:
        return 1500

    # Deduplicate: merge lines within 0.5pt, keep max length per position
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
        spacings.append(positions[i][0] - positions[i-1][0])

    # Find runs of ~17pt spacings (2+ consecutive)
    is_grid_spacing = [abs(s - grid_spacing) < grid_tol for s in spacings]

    # Mark positions that are part of grid runs
    grid_flags = [False] * len(positions)

    run_start = None
    for i in range(len(is_grid_spacing)):
        if is_grid_spacing[i]:
            if run_start is None:
                run_start = i
        else:
            if run_start is not None:
                run_len = i - run_start
                if run_len >= 2:
                    for j in range(run_start, i + 1):
                        grid_flags[j] = True
                run_start = None
    if run_start is not None:
        run_len = len(is_grid_spacing) - run_start
        if run_len >= 2:
            for j in range(run_start, len(positions)):
                grid_flags[j] = True

    # After grid run, find the room wall:
    # 1. First look for a non-grid position with a long-wall pair (> 200pt within 10pt)
    # 2. Fallback: first non-grid position
    best_with_long_pair = None
    best_non_grid = None

    for i in range(len(positions)):
        if grid_flags[i]:
            continue

        if best_non_grid is None:
            best_non_grid = i

        # Check if this position has a partner > 200pt within 10pt
        # Candidate must itself be a real wall (>= 60pt), not a door frame
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

    # Prefer the long-wall pair ONLY if it's close to the first non-grid position
    # (within 30pt). This avoids picking distant walls on the wrong side.
    if best_with_long_pair is not None and best_non_grid is not None:
        dist_pair = positions[best_with_long_pair][0]
        dist_first = positions[best_non_grid][0]
        if dist_pair <= dist_first * 1.5 and abs(dist_pair - dist_first) < 30:
            return dist_pair

    if best_non_grid is not None:
        return positions[best_non_grid][0]

    # All positions are grid
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
