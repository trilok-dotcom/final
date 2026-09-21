import math
from typing import Tuple, Dict, Any

# Georeferenced Bounding Box for Demo Satellite Region
DEFAULT_BOUNDS = {
    "north": 12.9800,  # Max Latitude (Top edge, y=0)
    "south": 12.9600,  # Min Latitude (Bottom edge, y=height)
    "west": 77.5800,   # Min Longitude (Left edge, x=0)
    "east": 77.6000,   # Max Longitude (Right edge, x=width)
}

IMAGE_WIDTH = 512
IMAGE_HEIGHT = 512


class GeoReferenceTransform:
    """Centralized, mathematically consistent georeferencing transform utility.

    Converts between geographic coordinates (Latitude, Longitude) and image pixels (x, y).

    Coordinate convention:
    - x: 0 to width (increases Eastwards / right)
    - y: 0 to height (increases Southwards / down)
    - Longitude: west to east (increases rightwards)
    - Latitude: south to north (increases UPWARDS)

    Formulas:
    x = (lon - west) / (east - west) * width
    y = (north - lat) / (north - south) * height

    lon = west + (x / width) * (east - west)
    lat = north - (y / height) * (north - south)
    """

    def __init__(
        self,
        bounds: Dict[str, float] = None,
        width: int = IMAGE_WIDTH,
        height: int = IMAGE_HEIGHT,
    ):
        self.bounds = bounds or DEFAULT_BOUNDS
        self.width = width
        self.height = height

    def geo_to_pixel(self, lat: float, lon: float) -> Tuple[int, int]:
        """Convert geographic coordinate (lat, lon) to pixel coordinate (x, y)."""
        lat_span = self.bounds["north"] - self.bounds["south"]
        lon_span = self.bounds["east"] - self.bounds["west"]

        norm_x = (float(lon) - self.bounds["west"]) / lon_span if lon_span != 0 else 0.5
        norm_y = (self.bounds["north"] - float(lat)) / lat_span if lat_span != 0 else 0.5

        x = int(round(norm_x * self.width))
        y = int(round(norm_y * self.height))

        # Clamp pixels within image dimensions
        x = max(0, min(self.width - 1, x))
        y = max(0, min(self.height - 1, y))

        return x, y

    def pixel_to_geo(self, x: float, y: float) -> Tuple[float, float]:
        """Convert pixel coordinate (x, y) to geographic coordinate (lat, lon)."""
        norm_x = max(0.0, min(1.0, float(x) / self.width))
        norm_y = max(0.0, min(1.0, float(y) / self.height))

        lon = self.bounds["west"] + norm_x * (self.bounds["east"] - self.bounds["west"])
        lat = self.bounds["north"] - norm_y * (self.bounds["north"] - self.bounds["south"])

        return round(lat, 6), round(lon, 6)

    def is_within_bounds(self, lat: float, lon: float) -> bool:
        """Check if target (lat, lon) falls strictly within the demo bounding box."""
        return (
            self.bounds["south"] <= float(lat) <= self.bounds["north"]
            and self.bounds["west"] <= float(lon) <= self.bounds["east"]
        )

    def get_bounds(self) -> Dict[str, float]:
        """Return current bounding box dictionary."""
        return self.bounds

    def get_center_geo(self) -> Tuple[float, float]:
        """Return center (lat, lon) coordinate of the bounding box."""
        center_lat = (self.bounds["north"] + self.bounds["south"]) / 2.0
        center_lon = (self.bounds["east"] + self.bounds["west"]) / 2.0
        return round(center_lat, 6), round(center_lon, 6)


georeference = GeoReferenceTransform()


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate geographic distance in kilometers between two lat/lon points using Haversine formula."""
    R = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c
