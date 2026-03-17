"""
Room Detection using vector ray-casting with smart grid-line skipping.
For each room label, casts rays in 4 directions using vector wall data.
Detects ceiling grid patterns per-ray and skips them to find actual walls.
"""

from typing import Optional

import numpy as np
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


def find_all_walls_in_direction(cx, cy, direction, wall_lines, min_dist=5, max_dist=1500):
    """
    Find ALL wall lines in a given direction from (cx, cy).
    Returns list of (distance, line) tuples sorted by distance.
    """
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
                        results.append((dist, line))
                elif direction == 'right' and wall_x > cx:
                    dist = wall_x - cx
                    if min_dist < dist < max_dist:
                        results.append((dist, line))

        elif direction in ('up', 'down') and is_h(line):
            wall_y = (line.y0 + line.y1) / 2
            x_min = min(line.x0, line.x1)
            x_max = max(line.x0, line.x1)
            if x_min - 10 <= cx <= x_max + 10:
                if direction == 'up' and wall_y < cy:
                    dist = cy - wall_y
                    if min_dist < dist < max_dist:
                        results.append((dist, line))
                elif direction == 'down' and wall_y > cy:
                    dist = wall_y - cy
                    if min_dist < dist < max_dist:
                        results.append((dist, line))

    results.sort(key=lambda x: x[0])
    return results


def has_wall_pair(dist, candidates, idx):
    """
    Check if a wall has a close partner indicating a structural double-wall.
    CAD structural walls are drawn as parallel double lines (0.5-8pt apart),
    or as duplicate/overlapping lines at the same position.
    Ceiling grid lines are single lines spaced at ~17pt.
    """
    for j, (od, _) in enumerate(candidates):
        if j == idx:
            continue
        gap = abs(dist - od)
        # Close pair: double-wall lines 0.5-8pt apart
        if 0.5 < gap < 8:
            return True
        # Duplicate: overlapping wall lines at same position
        if gap < 0.5:
            return True
    return False


def find_room_wall(cx, cy, direction, wall_lines, grid_spacing=17, grid_tolerance=3):
    """
    Find the actual room wall in a given direction, skipping ceiling grid lines.

    Strategy:
    1. Find all walls in the direction
    2. A wall is structural if it has a pair partner (double-wall or duplicate)
    3. A wall is grid if it has neighbors at ~17pt spacing
    4. Return the first structural or non-grid wall
    """
    candidates = find_all_walls_in_direction(cx, cy, direction, wall_lines, min_dist=3)

    if not candidates:
        return 1500  # No wall found

    for i, (dist, line) in enumerate(candidates):
        # Check 1: Does this wall have a pair partner? → structural wall
        if has_wall_pair(dist, candidates, i):
            return dist

        # Check 2: Is this wall part of a regular grid?
        is_grid = False
        for j, (other_dist, _) in enumerate(candidates):
            if i == j:
                continue
            spacing = abs(dist - other_dist)
            if abs(spacing - grid_spacing) < grid_tolerance:
                is_grid = True
                break
            if abs(spacing - 2 * grid_spacing) < grid_tolerance:
                is_grid = True
                break

        if not is_grid:
            return dist

    # All walls are grid lines → take the farthest one and add grid_spacing
    distances = [c[0] for c in candidates]
    return distances[-1] + grid_spacing / 2


def detect_rooms(pdf_data):
    """
    Room detection:
    1. For each room label, find walls in 4 directions
    2. Smart grid-line skipping per direction
    3. Calculate rectangular room area
    """
    # Use long wall lines only (structural + grid, both are long)
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

        centroid = (cx, cy)
        polygon_m = [(p[0] * pts_to_m, p[1] * pts_to_m) for p in polygon_pts]

        rooms.append(Room(
            name=label.text,
            polygon_pts=polygon_pts,
            polygon_m=polygon_m,
            area_m2=round(area_m2, 2),
            centroid_pts=centroid,
            confidence=0.80,
            source="auto"
        ))

    print(f"    Rooms detected: {len(rooms)}")
    return rooms
