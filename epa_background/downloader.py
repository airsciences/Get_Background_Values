"""Download and cache EPA's pre-generated AQS data files.

Replaces the workbook's "keep local CSV copies up to date" step: files are
fetched on demand from https://aqs.epa.gov/aqsweb/airdata/ and cached in
data_cache/ so a repeat run for the same year doesn't re-download.
"""

import io
import zipfile
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://aqs.epa.gov/aqsweb/airdata"
CACHE_DIR = Path(__file__).resolve().parent.parent / "data_cache"

ANNUAL_USECOLS = [
    "State Code", "County Code", "Site Num", "Parameter Code", "POC",
    "Latitude", "Longitude", "Parameter Name", "Sample Duration",
    "Pollutant Standard", "Year", "Units of Measure", "Event Type",
    "Observation Count", "Observation Percent", "Completeness Indicator",
    "Valid Day Count", "Arithmetic Mean", "2nd Max Value", "4th Max Value",
    "98th Percentile", "99th Percentile", "Local Site Name", "State Name",
]

DAILY_USECOLS = [
    "State Code", "County Code", "Site Num", "Parameter Code", "POC",
    "Latitude", "Longitude", "Pollutant Standard", "Date Local",
    "Units of Measure", "Event Type", "Observation Count",
    "Observation Percent", "Arithmetic Mean", "1st Max Value",
    "Local Site Name", "State Name", "Date of Last Change",
]


class EPADataUnavailable(Exception):
    """Raised when EPA hasn't published a requested year yet."""


def _cache_path(filename: str) -> Path:
    return CACHE_DIR / filename / f"{filename}.csv"


def _download_and_extract(filename: str, force_refresh: bool = False) -> Path:
    """Download <filename>.zip from EPA, extract the CSV, cache it locally."""
    csv_path = _cache_path(filename)
    if csv_path.exists() and not force_refresh:
        return csv_path

    url = f"{BASE_URL}/{filename}.zip"
    resp = requests.get(url, timeout=120)
    if resp.status_code == 404:
        raise EPADataUnavailable(
            f"EPA has not published {filename}.zip yet (404 at {url})."
        )
    resp.raise_for_status()

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        # the zip contains exactly one CSV named <filename>.csv
        member = f"{filename}.csv"
        if member not in zf.namelist():
            member = zf.namelist()[0]
        with zf.open(member) as src, open(csv_path, "wb") as dst:
            dst.write(src.read())

    return csv_path


def load_annual(year: int, force_refresh: bool = False) -> pd.DataFrame:
    """Load annual_conc_by_monitor_<year>, nationwide, all parameters."""
    filename = f"annual_conc_by_monitor_{year}"
    path = _download_and_extract(filename, force_refresh=force_refresh)
    df = pd.read_csv(path, usecols=lambda c: c in ANNUAL_USECOLS, low_memory=False)
    df["Year"] = year
    return df


def load_daily(parameter_or_code: str, year: int, force_refresh: bool = False) -> pd.DataFrame:
    """Load daily_<parameter_or_code>_<year>, e.g. daily_88101_2023 or daily_LEAD_2023."""
    filename = f"daily_{parameter_or_code}_{year}"
    path = _download_and_extract(filename, force_refresh=force_refresh)
    df = pd.read_csv(path, usecols=lambda c: c in DAILY_USECOLS, low_memory=False)
    df["Date Local"] = pd.to_datetime(df["Date Local"])
    return df


def try_latest_complete_year(default_guess: int) -> int:
    """Probe backwards from default_guess until an annual file is found on EPA's site."""
    year = default_guess
    for _ in range(5):
        url = f"{BASE_URL}/annual_conc_by_monitor_{year}.zip"
        try:
            head = requests.head(url, timeout=15)
            if head.status_code == 200:
                return year
        except requests.RequestException:
            pass
        year -= 1
    raise EPADataUnavailable("Could not find any published annual data in the last 5 years.")
