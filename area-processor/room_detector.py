"""
Room Detection using flood-fill on rasterized PDF.
Identifies enclosed regions (rooms) and maps them back to vector coordinates.
"""

from typing import Optional

import cv2
import numpy as np
from scipy.spatial import cKDTree
from shapely.geometry import Polygon, Point
from dataclasses import dataclass, field
from pdf_parser import PDFData, TextBlock
from config import (
    RASTER_DPI, MIN_ROOM_AREA_M2, MAX_ROOM_AREA_M2,
    MORPH_KERNEL_SIZE, VECTOR_SNAP_TOLERANCE
)


@dataclass
class Room:
    """A detected room with its properties."""
    name: Optional[str] = None
    polygon_pts: list = field(default_factory=list)  # PDF coordinates
    polygon_m: list = field(default_factory=list)  # Real-world meters
    area_m2: float = 0.0
    centroid_pts: tuple = (0.0, 0.0)
    confidence: float = 0.0
    source: str = "auto"


def rasterize_walls(pdf_data: PDFData, dpi: int = RASTER_DPI) -> tuple:
    """
    Create a binary image of walls from vector data.
    Returns: (binary_image, scale_x, scale_y) where scale maps pixels to PDF points.
    """
    # Calculate pixel dimensions
    pts_per_inch = 72
    scale = dpi / pts_per_inch
    width_px = int(pdf_data.page_width * scale)
    height_px = int(pdf_data.page_height * scale)

    # Create blank white image
    img = np.ones((height_px, width_px), dtype=np.uint8) * 255

    # Draw wall lines as black
    for line in pdf_data.wall_lines:
        x0 = int(line.x0 * scale)
        y0 = int(line.y0 * scale)
        x1 = int(line.x1 * scale)
        y1 = int(line.y1 * scale)
        thickness = max(2, int(line.width * scale * 1.5))
        cv2.line(img, (x0, y0), (x1, y1), 0, thickness)

    # Morphological closing to seal micro-gaps
    kernel = np.ones((MORPH_KERNEL_SIZE, MORPH_KERNEL_SIZE), np.uint8)
    img = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel)

    return img, scale


def flood_fill_rooms(binary_img: np.ndarray, pdf_data: PDFData, px_scale: float) -> list:
    """
    Use flood-fill from room label positions to detect rooms.
    Returns list of (contour_pixels, label) tuples.
    """
    h, w = binary_img.shape
    rooms_found = []
    filled = binary_img.copy()
    used_mask = np.zeros((h, w), dtype=np.uint8)

    # Use room labels as seed points
    for label in pdf_data.room_labels:
        cx = int(label.center[0] * px_scale)
        cy = int(label.center[1] * px_scale)

        # Ensure within bounds
        if cx < 0 or cx >= w or cy < 0 or cy >= h:
            continue

        # Skip if already filled or on a wall
        if used_mask[cy, cx] > 0 or filled[cy, cx] == 0:
            continue

        # Flood fill
        mask = np.zeros((h + 2, w + 2), dtype=np.uint8)
        _, _, flood_mask, _ = cv2.floodFill(
            filled.copy(), mask, (cx, cy), 128,
            loDiff=0, upDiff=0
        )

        # Extract filled region
        region = (flood_mask[1:-1, 1:-1] == 1).astype(np.uint8) * 255

        # Skip tiny or huge regions
        pixel_area = cv2.countNonZero(region)
        if pixel_area < 100:
            continue

        # Find contours
        contours, _ = cv2.findContours(region, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            largest = max(contours, key=cv2.contourArea)
            rooms_found.append((largest, label))
            cv2.drawContours(used_mask, [largest], -1, 255, -1)

    # Also try flood-fill from grid points for unlabeled rooms
    step = int(50 * px_scale)  # ~50pt grid
    for y in range(step, h - step, step):
        for x in range(step, w - step, step):
            if used_mask[y, x] > 0 or filled[y, x] == 0:
                continue

            mask = np.zeros((h + 2, w + 2), dtype=np.uint8)
            _, _, flood_mask, _ = cv2.floodFill(
                filled.copy(), mask, (x, y), 128,
                loDiff=0, upDiff=0
            )

            region = (flood_mask[1:-1, 1:-1] == 1).astype(np.uint8) * 255
            pixel_area = cv2.countNonZero(region)
            if pixel_area < 100:
                continue

            contours, _ = cv2.findContours(region, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                largest = max(contours, key=cv2.contourArea)
                rooms_found.append((largest, None))
                cv2.drawContours(used_mask, [largest], -1, 255, -1)

    return rooms_found


def snap_contour_to_vectors(contour_px: np.ndarray, pdf_data: PDFData,
                            px_scale: float) -> list:
    """
    Snap pixel-based contour points to nearest vector wall coordinates.
    This converts approximate pixel contours to exact vector polygons.
    """
    if len(pdf_data.wall_lines) == 0:
        # No walls to snap to — just convert pixel coords to PDF coords
        pts = []
        for point in contour_px.reshape(-1, 2):
            pts.append((point[0] / px_scale, point[1] / px_scale))
        return pts

    # Build KD-tree from wall line endpoints
    wall_points = []
    for line in pdf_data.wall_lines:
        wall_points.append([line.x0, line.y0])
        wall_points.append([line.x1, line.y1])
    wall_tree = cKDTree(np.array(wall_points))

    # Simplify contour to reduce points
    epsilon = 2.0 * px_scale
    simplified = cv2.approxPolyDP(contour_px, epsilon, True)

    snapped = []
    for point in simplified.reshape(-1, 2):
        # Convert pixel to PDF coordinates
        pdf_x = point[0] / px_scale
        pdf_y = point[1] / px_scale

        # Find nearest wall point
        dist, idx = wall_tree.query([pdf_x, pdf_y])

        if dist < VECTOR_SNAP_TOLERANCE:
            # Snap to wall point
            snapped.append(tuple(wall_points[idx]))
        else:
            # Keep original (converted) point
            snapped.append((pdf_x, pdf_y))

    return snapped


def calculate_area(polygon_pts: list, pts_to_m: float) -> float:
    """
    Calculate room area in square meters using Shapely (Shoelace formula).
    """
    if len(polygon_pts) < 3:
        return 0.0

    try:
        poly = Polygon(polygon_pts)
        if not poly.is_valid:
            poly = poly.buffer(0)
        area_pts2 = poly.area
        area_m2 = area_pts2 * (pts_to_m ** 2)
        return round(area_m2, 2)
    except Exception:
        return 0.0


def match_room_name(polygon_pts: list, text_blocks: list) -> Optional[str]:
    """
    Find the room name by checking which text block falls inside the polygon.
    Uses point-in-polygon test.
    """
    if len(polygon_pts) < 3:
        return None

    try:
        poly = Polygon(polygon_pts)
        if not poly.is_valid:
            poly = poly.buffer(0)

        for tb in text_blocks:
            point = Point(tb.center)
            if poly.contains(point):
                return tb.text
    except Exception:
        pass

    return None


def detect_rooms(pdf_data: PDFData) -> list:
    """
    Main room detection pipeline.
    Returns list of Room objects with names and areas.
    """
    # Step 1: Rasterize walls
    binary_img, px_scale = rasterize_walls(pdf_data)

    # Step 2: Flood-fill to find rooms
    raw_rooms = flood_fill_rooms(binary_img, pdf_data, px_scale)

    # Step 3: Process each room
    rooms = []
    for contour, label in raw_rooms:
        # Snap to vector coordinates
        polygon_pts = snap_contour_to_vectors(contour, pdf_data, px_scale)

        if len(polygon_pts) < 3:
            continue

        # Calculate area
        area_m2 = calculate_area(polygon_pts, pdf_data.pts_to_m)

        # Filter by area
        if area_m2 < MIN_ROOM_AREA_M2 or area_m2 > MAX_ROOM_AREA_M2:
            continue

        # Match room name
        name = None
        if label:
            name = label.text
        else:
            name = match_room_name(polygon_pts, pdf_data.room_labels)

        # Calculate centroid
        try:
            poly = Polygon(polygon_pts)
            centroid = (poly.centroid.x, poly.centroid.y)
        except Exception:
            centroid = polygon_pts[0] if polygon_pts else (0, 0)

        # Convert polygon to real-world meters
        polygon_m = [
            (p[0] * pdf_data.pts_to_m, p[1] * pdf_data.pts_to_m)
            for p in polygon_pts
        ]

        room = Room(
            name=name,
            polygon_pts=polygon_pts,
            polygon_m=polygon_m,
            area_m2=area_m2,
            centroid_pts=centroid,
            confidence=0.9 if label else 0.7,
            source="auto"
        )
        rooms.append(room)

    return rooms
