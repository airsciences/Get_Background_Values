"""PM10 24-hour design value (PM10 Multiyear tab equivalent).

NAAQS form: "not to be exceeded more than once per year on average over 3
years." Implemented, as the workbook does, by taking each year's top-4
daily 24-hour values, pooling all 12 (4 x 3 years) candidates, and taking
the pooled 4th-highest.
"""

from dataclasses import dataclass

import pandas as pd

from . import downloader
from .pollutants import Standard


@dataclass
class PM10YearTop4:
    calendar_year: int
    top4: list[float]


@dataclass
class PM10MultiyearResult:
    site_name: str
    per_year: list[PM10YearTop4]
    design_value: float | None
    unit: str | None


def _site_daily_series(site_name: str, standard_label: str, calendar_year: int) -> pd.Series:
    df = downloader.load_daily("81102", calendar_year)
    mask = (df["Pollutant Standard"] == standard_label) & (df["Local Site Name"] == site_name)
    matched = df[mask].copy()
    if matched.empty:
        return pd.Series(dtype=float)

    # disambiguate duplicate POC/method rows for the same date the way the
    # workbook does: keep the row with the most recent "Date of Last Change"
    matched = matched.sort_values("Date of Last Change").drop_duplicates(subset="Date Local", keep="last")
    return matched.set_index(matched["Date Local"].dt.date)["Arithmetic Mean"]


def compute_pm10_multiyear(standard: Standard, site_name: str, calendar_years: list[int]) -> PM10MultiyearResult:
    per_year: list[PM10YearTop4] = []
    unit = None

    for year in calendar_years:
        series = _site_daily_series(site_name, standard.aqs_standard_label, year)
        top4 = sorted(series.dropna().tolist(), reverse=True)[:4]
        per_year.append(PM10YearTop4(calendar_year=year, top4=top4))
        if unit is None and not series.empty:
            df = downloader.load_daily("81102", year)
            row = df[(df["Pollutant Standard"] == standard.aqs_standard_label) & (df["Local Site Name"] == site_name)]
            if not row.empty:
                unit = str(row.iloc[0].get("Units of Measure", ""))

    pooled = sorted((v for yp in per_year for v in yp.top4), reverse=True)
    design_value = pooled[3] if len(pooled) >= 4 else None

    return PM10MultiyearResult(site_name=site_name, per_year=per_year, design_value=design_value, unit=unit)
