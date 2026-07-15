"""Find candidate monitors for a facility + pollutant standard + radius.

Equivalent to the workbook's "Stations" tab candidate list, but using a true
haversine radius instead of a lat/long bounding box.
"""

from dataclasses import dataclass

import pandas as pd

from . import downloader
from .geo import haversine_km


@dataclass
class MonitorCandidate:
    site_name: str
    state_name: str
    county_code: str
    site_num: str
    latitude: float
    longitude: float
    distance_km: float
    observation_count: int
    completeness_indicator: str
    year: int


def find_candidates(
    facility_lat: float,
    facility_lon: float,
    radius_km: float,
    aqs_standard_label: str,
    reference_year: int,
) -> list[MonitorCandidate]:
    """Monitors reporting `aqs_standard_label` within `radius_km` of the facility,
    using `reference_year`'s annual file as the site/coordinate universe."""
    df = downloader.load_annual(reference_year)
    df = df[df["Pollutant Standard"] == aqs_standard_label].copy()
    if df.empty:
        return []

    df["distance_km"] = haversine_km(facility_lat, facility_lon, df["Latitude"], df["Longitude"])
    df = df[df["distance_km"] <= radius_km]
    if df.empty:
        return []

    df = df.sort_values("distance_km")
    df = df.drop_duplicates(subset=["Local Site Name"], keep="first")

    candidates = []
    for _, row in df.iterrows():
        candidates.append(
            MonitorCandidate(
                site_name=row["Local Site Name"],
                state_name=row.get("State Name", ""),
                county_code=str(row.get("County Code", "")),
                site_num=str(row.get("Site Num", "")),
                latitude=float(row["Latitude"]),
                longitude=float(row["Longitude"]),
                distance_km=round(float(row["distance_km"]), 2),
                observation_count=int(row.get("Observation Count", 0) or 0),
                completeness_indicator=str(row.get("Completeness Indicator", "")),
                year=reference_year,
            )
        )
    return candidates
