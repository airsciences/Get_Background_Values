"""Lead (Pb) rolling 3-month design value.

NOTE: unlike every other calculator in this package, this one has no
equivalent tab in the source workbook to validate against -- the workbook
downloads daily Lead data but never computes a background value from it.
This is new logic based on 40 CFR Part 50 Appendix R: the standard (0.15
ug/m3) is evaluated as the maximum arithmetic 3-month mean concentration
over the most recent 3-year period. Treat this calculator's output with
more skepticism than the others until it's checked against a known example.

Also unconfirmed: the exact "Pollutant Standard" string EPA uses for Lead
in the daily summary files (assumed "Pb 3-Month 2008" below, EPA's AQS
naming convention). No local reference data was available to verify this
label -- if the app returns zero matches for a Lead monitor that clearly
exists, check this first.
"""

from dataclasses import dataclass

import pandas as pd

from . import downloader
from .pollutants import Standard


@dataclass
class LeadResult:
    site_name: str
    monthly_means: dict[str, float]  # "YYYY-MM" -> monthly arithmetic mean
    rolling_3mo_means: dict[str, float]  # "YYYY-MM" (window-ending month) -> 3-mo rolling mean
    design_value: float | None
    unit: str | None


def compute_lead_design_value(standard: Standard, site_name: str, calendar_years: list[int]) -> LeadResult:
    frames = []
    unit = None
    for year in calendar_years:
        df = downloader.load_daily("LEAD", year)
        matched = df[(df["Pollutant Standard"] == standard.aqs_standard_label) & (df["Local Site Name"] == site_name)]
        if not matched.empty:
            frames.append(matched)
            if unit is None:
                unit = str(matched.iloc[0].get("Units of Measure", ""))

    if not frames:
        return LeadResult(site_name=site_name, monthly_means={}, rolling_3mo_means={}, design_value=None, unit=None)

    combined = pd.concat(frames)
    combined["year_month"] = combined["Date Local"].dt.to_period("M")

    monthly = combined.groupby("year_month")["Arithmetic Mean"].mean().sort_index()
    # fill any gap months so a 3-month rolling window doesn't silently skip a missing month
    full_index = pd.period_range(monthly.index.min(), monthly.index.max(), freq="M")
    monthly = monthly.reindex(full_index)

    rolling = monthly.rolling(window=3, min_periods=3).mean()

    design_value = float(rolling.max()) if rolling.notna().any() else None

    return LeadResult(
        site_name=site_name,
        monthly_means={str(k): float(v) for k, v in monthly.items() if pd.notna(v)},
        rolling_3mo_means={str(k): float(v) for k, v in rolling.items() if pd.notna(v)},
        design_value=design_value,
        unit=unit,
    )
