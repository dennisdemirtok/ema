import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
STORAGE_BUCKET = "area-pdfs"

# Processing settings
RASTER_DPI = 300
MIN_ROOM_AREA_M2 = 1.0
MAX_ROOM_AREA_M2 = 500.0
WALL_STROKE_MIN = 0.3  # Minimum stroke width to be considered a wall (points)
VECTOR_SNAP_TOLERANCE = 2.0  # Points tolerance for snapping to vectors
MORPH_KERNEL_SIZE = 3  # Morphological closing kernel size
KNOWN_SCALES = [50, 100, 200, 500]
DEFAULT_SCALE = 100
