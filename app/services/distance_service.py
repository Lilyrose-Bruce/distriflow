"""
distance_service.py - asks OSRM for real ROAD distances and driving times.
If OSRM fails, it falls back to straight-line (Haversine) distances.
"""
import math
from typing import List, Tuple
import requests

from app import config
from app.services.errors import DistanceServiceError

Point = Tuple[float, float]          # (latitude, longitude)
Matrix = List[List[float]]


class DistanceService:
    def get_matrix(self, points: List[Point]) -> Tuple[Matrix, Matrix]:
        raise NotImplementedError


class OsrmDistanceService(DistanceService):
    def __init__(self, base_url: str = None, timeout_seconds: int = None):
        self.base_url = (base_url or config.OSRM_BASE_URL).rstrip("/")
        self.timeout_seconds = timeout_seconds or config.OSRM_TIMEOUT_SECONDS

    def get_matrix(self, points: List[Point]) -> Tuple[Matrix, Matrix]:
        # 1. If coordinates are missing entirely, fall back
        if not points or any(lat is None or lon is None for lat, lon in points):
            print("WARNING: Missing coordinates. Falling back to straight-line distances.")
            return self._fallback_matrix(points)
            
        # 2. If coordinates are 0.0 (unconfigured depot or customers), fall back
        if any(lat == 0.0 and lon == 0.0 for lat, lon in points):
            print("WARNING: Coordinates are 0.0 (unconfigured). Falling back to straight-line.")
            return self._fallback_matrix(points)

        coordinates = ";".join(f"{lon:.6f},{lat:.6f}" for lat, lon in points)
        url = f"{self.base_url}/table/v1/driving/{coordinates}"

        try:
            response = requests.get(
                url,
                params={"annotations": "duration,distance"},
                timeout=self.timeout_seconds,
            )
            
            # 3. Instead of raising an error on 404, print a warning and fall back
            if response.status_code != 200:
                print(f"WARNING: OSRM returned HTTP {response.status_code}. Falling back to straight-line distances.")
                return self._fallback_matrix(points)
            
            data = response.json()
            if data.get("code") != "Ok":
                print(f"WARNING: OSRM error ({data.get('code')}). Falling back to straight-line distances.")
                return self._fallback_matrix(points)

            return data["distances"], data["durations"]

        except Exception as error:
            print(f"WARNING: OSRM connection failed ({error}). Falling back to straight-line distances.")
            return self._fallback_matrix(points)

    def _fallback_matrix(self, points: List[Point]) -> Tuple[Matrix, Matrix]:
        """Straight-line distance (Haversine) + estimated time at 40km/h."""
        size = len(points)
        distances = [[0.0] * size for _ in range(size)]
        durations = [[0.0] * size for _ in range(size)]

        for i in range(size):
            for j in range(size):
                if i != j:
                    # Safely unpack, defaulting to 0.0 ONLY if it is None
                    lat1 = points[i][0] if points[i][0] is not None else 0.0
                    lon1 = points[i][1] if points[i][1] is not None else 0.0
                    lat2 = points[j][0] if points[j][0] is not None else 0.0
                    lon2 = points[j][1] if points[j][1] is not None else 0.0
                    
                    # Haversine distance in meters
                    R = 6371000
                    phi1, phi2 = math.radians(lat1), math.radians(lat2)
                    dphi = math.radians(lat2 - lat1)
                    dlambda = math.radians(lon2 - lon1)
                    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
                    distance = 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))
                    
                    distances[i][j] = distance
                    # Assume 40 km/h (11.11 m/s)
                    durations[i][j] = distance / 11.11

        return distances, durations


def get_distance_service() -> DistanceService:
    return OsrmDistanceService()