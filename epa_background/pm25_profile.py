"""PM2.5 seasonal background profile (PM2.5 Profile tab equivalent).

(EPA 2024) Guidance on Developing Background Concentrations for Use in
Modeling Demonstrations, and Appendix N to 40 CFR Part 50: for each of 3
EPA "monitoring years" (Dec 1 of year-1 through Nov 30 of year), compute the
site's 98th-percentile daily value, drop days above that threshold, then
take the maximum of what's left within each season. Average each season's
max across the 3 years.
"""

import math
from dataclasses import dataclass

import pandas as pd

from . import downloader
from .pollutants import Standard

SEASON_BY_MONTH = {
    12: "Winter", 1: "Winter", 2: "Winter",
    3: "Spring", 4: "Spring", 5: "Spring",
    6: "Summer", 7: "Summer", 8: "Summer",
    9: "Fall", 10: "Fall", 11: "Fall",
}


@dataclass
class YearProfile:
    monitoring_year: int  # the "year" in Dec(year-1)-Nov(year)
    valid_days: int
    percentile_98_rank: int
    percentile_98_value: float | None
    seasonal_max: dict[str, float]


@dataclass
class PM25ProfileResult:
    site_name: str
    per_year: list[YearProfile]
    seasonal_3yr_average: dict[str, float | None]


def _site_daily_series(site_name: str, standard_label: str, calendar_year: int) -> pd.Series:
    df = downloader.load_daily("88101", calendar_year)
    mask = (df["Pollutant Standard"] == standard_label) & (df["Local Site Name"] == site_name)
    matched = df[mask]
    if matched.empty:
        return pd.Series(dtype=float)
    # collapse any duplicate POC/method rows for the same date by averaging
    return matched.groupby(matched["Date Local"].dt.date)["Arithmetic Mean"].mean()


def compute_pm25_profile(standard: Standard, site_name: str, monitoring_years: list[int]) -> PM25ProfileResult:
    per_year: list[YearProfile] = []

    for monitoring_year in monitoring_years:
        start = pd.Timestamp(monitoring_year - 1, 12, 1)
        end = pd.Timestamp(monitoring_year, 11, 30)

        prev_year_series = _site_daily_series(site_name, standard.aqs_standard_label, monitoring_year - 1)
        this_year_series = _site_daily_series(site_name, standard.aqs_standard_label, monitoring_year)
        combined = pd.concat([prev_year_series, this_year_series])
        combined.index = pd.to_datetime(combined.index)
        combined = combined[(combined.index >= start) & (combined.index <= end)]

        valid_days = int(combined.count())
        if valid_days == 0:
            per_year.append(YearProfile(monitoring_year, 0, 0, None, {s: None for s in ("Winter", "Spring", "Summer", "Fall")}))
            continue

        rank_98 = math.ceil(valid_days * 0.02) or 1
        sorted_desc = combined.sort_values(ascending=False)
        percentile_98_value = float(sorted_desc.iloc[rank_98 - 1])

        below_threshold = combined[combined <= percentile_98_value]

        seasonal_max = {}
        for season in ("Winter", "Spring", "Summer", "Fall"):
            season_mask = below_threshold.index.month.map(SEASON_BY_MONTH.get) == season
            season_values = below_threshold[season_mask]
            seasonal_max[season] = float(season_values.max()) if len(season_values) else None

        per_year.append(YearProfile(monitoring_year, valid_days, rank_98, percentile_98_value, seasonal_max))

    seasonal_3yr_average: dict[str, float | None] = {}
    for season in ("Winter", "Spring", "Summer", "Fall"):
        values = [yp.seasonal_max[season] for yp in per_year if yp.seasonal_max.get(season) is not None]
        seasonal_3yr_average[season] = round(sum(values) / len(values), 1) if values else None

    return PM25ProfileResult(site_name=site_name, per_year=per_year, seasonal_3yr_average=seasonal_3yr_average)
