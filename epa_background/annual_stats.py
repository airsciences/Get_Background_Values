"""Per-standard background statistic from annual_conc_by_monitor files.

Reimplements the Summary tab's per-row logic: pull one EPA-published
statistic column for a chosen monitor across N years, then combine those
years per `year_form` ("average" or "most_recent").
"""

from dataclasses import dataclass

from . import downloader
from .pollutants import ANNUAL_STAT_COLUMNS, Standard


@dataclass
class AnnualStatResult:
    standard_key: str
    site_name: str
    years_used: list[int]
    yearly_values: dict[int, float]
    combined_value: float | None
    unit: str | None
    year_form: str


def compute_annual_stat(
    standard: Standard,
    site_name: str,
    years: list[int],
    year_form: str | None = None,
) -> AnnualStatResult:
    year_form = year_form or standard.default_year_form
    column = ANNUAL_STAT_COLUMNS[standard.stat_column]

    yearly_values: dict[int, float] = {}
    unit = None

    for year in years:
        df = downloader.load_annual(year)
        mask = (
            (df["Pollutant Standard"] == standard.aqs_standard_label)
            & (df["Local Site Name"] == site_name)
        )
        matched = df[mask]
        if matched.empty:
            continue
        row = matched.iloc[0]
        value = row.get(column)
        if value is not None and value == value:  # not NaN
            yearly_values[year] = float(value)
            unit = unit or str(row.get("Units of Measure", ""))

    if not yearly_values:
        combined = None
    elif year_form == "most_recent":
        combined = yearly_values[max(yearly_values)]
    else:  # average
        combined = sum(yearly_values.values()) / len(yearly_values)

    return AnnualStatResult(
        standard_key=standard.key,
        site_name=site_name,
        years_used=sorted(yearly_values.keys()),
        yearly_values=yearly_values,
        combined_value=combined,
        unit=unit,
        year_form=year_form,
    )
