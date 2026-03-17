"""
Room Detection using watershed segmentation on rasterized PDF.
Uses PyMuPDF's native rasterization, extracts wall-only features,
then applies marker-controlled watershed from room label positions.
"""

from typing import Optional

import fitz  # PyMuPDF
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

# DPI for room detection (lower = faster, walls merge better)
DETECT_DPI = 150
# Minimum wall segment length in PDF points for line-kernel extraction
WALL_LINE_MIN_PT = 15


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


def rasterize_and_extract_walls(pdf_data, dpi=DETECT_DPI):
    """
    Rasterize PDF and extract wall-only features using morphological line detection.

    Strategy:
    1. Render PDF at target DPI
    2. Threshold to get all dark content (walls + text + symbols)
    3. Use morphological opening with horizontal/vertical line kernels
       to keep only long line features (walls) and remove text/symbols
    4. Dilate walls slightly for connectivity

    Returns: (walls_mask, rooms_mask, gray_image, zoom_factor)
    """
    doc = fitz.open(pdf_data.pdf_path)
    page = doc[0]

    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)

    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    # Threshold: dark pixels = walls/lines/text
    _, all_dark = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

    # Extract only long horizontal and vertical line features (walls)
    # This removes text, symbols, and short details
    wall_len_px = int(WALL_LINE_MIN_PT * zoom)

    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (wall_len_px, 1))
    h_walls = cv2.morphologyEx(all_dark, cv2.MORPH_OPEN, h_kernel)

    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, wall_len_px))
    v_walls = cv2.morphologyEx(all_dark, cv2.MORPH_OPEN, v_kernel)

    walls = cv2.bitwise_or(h_walls, v_walls)

    # Slightly thicken walls for better connectivity
    walls = cv2.dilate(walls, np.ones((3, 3), np.uint8), iterations=1)

    rooms = cv2.bitwise_not(walls)

    doc.close()
    return walls, rooms, gray, zoom


def find_seed_point(binary_img, center_x, center_y, search_radius=50):
    """
    Find a white (open space) pixel near the given center point.
    Room labels often sit on top of their own text (dark pixels),
    so we search outward to find nearby open space.
    """
    h, w = binary_img.shape

    if (0 <= center_x < w and 0 <= center_y < h
            and binary_img[center_y, center_x] == 255):
        return center_x, center_y

    # Spiral search outward
    for radius in range(1, search_radius + 1):
        for dx in range(-radius, radius + 1):
            for dy in [-radius, radius]:
                nx, ny = center_x + dx, center_y + dy
                if 0 <= nx < w and 0 <= ny < h and binary_img[ny, nx] == 255:
                    return nx, ny
        for dy in range(-radius + 1, radius):
            for dx in [-radius, radius]:
                nx, ny = center_x + dx, center_y + dy
                if 0 <= nx < w and 0 <= ny < h and binary_img[ny, nx] == 255:
                    return nx, ny

    return None


def watershed_rooms(walls, rooms_img, pdf_data, px_scale):
    """
    Use marker-controlled watershed to segment rooms.

    Strategy:
    - Each room label becomes a seed marker
    - Wall pixels become barrier markers (prevents expansion through walls)
    - Watershed expands each seed region until it hits walls or another region
    - This naturally handles door openings (narrow passages between rooms)

    Returns: list of (contour, label, area_m2) tuples
    """
    h, w = walls.shape

    # Initialize markers
    markers = np.zeros((h, w), dtype=np.int32)

    # Wall pixels = barrier marker (id=1)
    markers[walls > 0] = 1

    # Place room label seeds
    marker_id = 2
    marker_map = {}  # id -> TextBlock label
    search_radius = int(20 * px_scale)

    for label in pdf_data.room_labels:
        cx = int(label.center[0] * px_scale)
        cy = int(label.center[1] * px_scale)
        seed = find_seed_point(rooms_img, cx, cy, search_radius)
        if seed:
            sx, sy = seed
            if markers[sy, sx] == 0:  # not on a wall
                markers[sy, sx] = marker_id
                marker_map[marker_id] = label
                marker_id += 1

    # Watershed: walls image as gradient (high at walls, low at open space)
    gradient = cv2.cvtColor(walls, cv2.COLOR_GRAY2BGR)
    cv2.watershed(gradient, markers)

    # Extract results
    results = []
    for mid, label in marker_map.items():
        region = (markers == mid).astype(np.uint8) * 255
        pixel_area = cv2.countNonZero(region)
        area_m2 = pixel_area * (pdf_data.pts_to_m ** 2) / (px_scale ** 2)

        if area_m2 < MIN_ROOM_AREA_M2 or area_m2 > MAX_ROOM_AREA_M2:
            continue

        # Extract contour
        contours, _ = cv2.findContours(region, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            largest = max(contours, key=cv2.contourArea)
            results.append((largest, label, area_m2))

    return results


def snap_contour_to_vectors(contour_px, pdf_data, px_scale):
    """Snap pixel-based contour points to nearest vector wall coordinates."""
    epsilon = 2.0 * px_scale
    simplified = cv2.approxPolyDP(contour_px, epsilon, True)

    if len(pdf_data.wall_lines) == 0:
        pts = []
        for point in simplified.reshape(-1, 2):
            pts.append((point[0] / px_scale, point[1] / px_scale))
        return pts

    # Build KD-tree from wall line endpoints
    wall_points = []
    for line in pdf_data.wall_lines:
        wall_points.append([line.x0, line.y0])
        wall_points.append([line.x1, line.y1])
    wall_arr = np.array(wall_points)
    wall_tree = cKDTree(wall_arr)

    snapped = []
    for point in simplified.reshape(-1, 2):
        pdf_x = point[0] / px_scale
        pdf_y = point[1] / px_scale

        dist, idx = wall_tree.query([pdf_x, pdf_y])

        if dist < VECTOR_SNAP_TOLERANCE:
            snapped.append(tuple(wall_arr[idx]))
        else:
            snapped.append((pdf_x, pdf_y))

    return snapped


def calculate_area(polygon_pts, pts_to_m):
    """Calculate room area in m2 using Shapely (Shoelace formula)."""
    if len(polygon_pts) < 3:
        return 0.0
    try:
        poly = Polygon(polygon_pts)
        if not poly.is_valid:
            poly = poly.buffer(0)
        return round(poly.area * (pts_to_m ** 2), 2)
    except Exception:
        return 0.0


def match_room_name(polygon_pts, text_blocks):
    """Find room name by point-in-polygon test on text blocks."""
    if len(polygon_pts) < 3:
        return None
    try:
        poly = Polygon(polygon_pts)
        if not poly.is_valid:
            poly = poly.buffer(0)
        for tb in text_blocks:
            if poly.contains(Point(tb.center)):
                return tb.text
    except Exception:
        pass
    return None


def detect_rooms(pdf_data):
    """
    Main room detection pipeline.
    1. Rasterize PDF and extract wall-only features
    2. Watershed segmentation from room labels
    3. Snap contours to vector coordinates
    4. Calculate areas
    """
    # Step 1: Rasterize and extract walls
    print("    Rasterizing PDF and extracting walls...")
    walls, rooms_img, gray, px_scale = rasterize_and_extract_walls(pdf_data)
    h, w = walls.shape
    print(f"    Image: {w}x{h} px (DPI={DETECT_DPI})")

    # Step 2: Watershed segmentation
    print("    Running watershed segmentation...")
    raw_rooms = watershed_rooms(walls, rooms_img, pdf_data, px_scale)
    print(f"    Raw candidates: {len(raw_rooms)}")

    # Step 3: Process each room
    rooms = []
    for contour, label, ws_area in raw_rooms:
        polygon_pts = snap_contour_to_vectors(contour, pdf_data, px_scale)

        if len(polygon_pts) < 3:
            continue

        # Use watershed area (more accurate than polygon area for irregular shapes)
        area_m2 = ws_area

        # Also compute polygon area as cross-check
        poly_area = calculate_area(polygon_pts, pdf_data.pts_to_m)

        if area_m2 < MIN_ROOM_AREA_M2 or area_m2 > MAX_ROOM_AREA_M2:
            continue

        name = label.text if label else match_room_name(polygon_pts, pdf_data.room_labels)

        # Centroid
        try:
            poly = Polygon(polygon_pts)
            centroid = (poly.centroid.x, poly.centroid.y)
        except Exception:
            centroid = polygon_pts[0] if polygon_pts else (0, 0)

        # Convert to meters
        polygon_m = [(p[0] * pdf_data.pts_to_m, p[1] * pdf_data.pts_to_m) for p in polygon_pts]

        rooms.append(Room(
            name=name,
            polygon_pts=polygon_pts,
            polygon_m=polygon_m,
            area_m2=round(area_m2, 2),
            centroid_pts=centroid,
            confidence=0.85 if label else 0.6,
            source="auto"
        ))

    return rooms
