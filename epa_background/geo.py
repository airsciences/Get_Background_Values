"""Great-circle distance helpers."""

import math

import numpy as np

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2, lon2) -> "float | np.ndarray":
    """Great-circle distance in km. lat2/lon2 may be scalars or numpy arrays."""
    lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
    lat2_r = np.radians(lat2)
    lon2_r = np.radians(lon2)

    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r

    a = np.sin(dlat / 2) ** 2 + math.cos(lat1_r) * np.cos(lat2_r) * np.sin(dlon / 2) ** 2
    c = 2 * np.arcsin(np.sqrt(a))
    return EARTH_RADIUS_KM * c
