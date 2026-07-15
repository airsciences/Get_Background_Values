"""Pollutant / NAAQS standard configuration.

Mirrors the standards tracked in "AirSci Get Background Values_v1.10.xlsm"
(Stations / Summary / PM2.5 Profile / PM10 Multiyear tabs), reimplemented
against EPA's pre-generated AQS data files instead of local CSV copies.

Each entry in STANDARDS describes one NAAQS "Pollutant Standard" as EPA's
AQS files label it. `method` selects which calculation module handles it:

- "annual_stat": pull one statistic column from the annual_conc_by_monitor
  file for each of 3 years, then combine per `year_form`.
- "pm25_seasonal_profile": PM2.5 Profile tab logic (seasonal 98th-percentile
  background profile from daily data).
- "pm10_multiyear_4th_high": PM10 Multiyear tab logic (4th-highest 24-hr
  value pooled across 3 years, from daily data).
- "lead_rolling_3mo": Pb NAAQS logic (max rolling 3-month average over 3
  years, from daily data) -- new logic, no equivalent tab in the workbook.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Standard:
    key: str                     # short id used in the UI / form fields
    pollutant_group: str         # which radius input this standard shares (CO, NO2, Ozone, PM10, PM2.5, SO2, Lead)
    parameter_code: str          # AQS numeric parameter code
    aqs_standard_label: str      # exact "Pollutant Standard" string in the annual/daily CSVs
    method: str
    stat_column: Optional[str] = None   # annual_conc_by_monitor column used for annual_stat
    default_year_form: str = "average"  # "average" | "most_recent"
    daily_file_code: Optional[str] = None  # parameter code (or "LEAD") used in daily_<code>_<year> filenames
    display_name: str = ""
    unit_hint: str = ""


STANDARDS = [
    Standard(
        key="co_1hr", pollutant_group="CO", parameter_code="42101",
        aqs_standard_label="CO 1-hour 1971", method="annual_stat",
        stat_column="second_max_value", default_year_form="most_recent",
        display_name="CO 1-hour (1971)", unit_hint="ppm",
    ),
    Standard(
        key="co_8hr", pollutant_group="CO", parameter_code="42101",
        aqs_standard_label="CO 8-hour 1971", method="annual_stat",
        stat_column="second_max_value", default_year_form="most_recent",
        display_name="CO 8-hour (1971)", unit_hint="ppm",
    ),
    Standard(
        key="no2_1hr", pollutant_group="NO2", parameter_code="42602",
        aqs_standard_label="NO2 1-hour 2010", method="annual_stat",
        stat_column="98th_percentile", default_year_form="average",
        display_name="NO2 1-hour (2010)", unit_hint="ppb",
    ),
    Standard(
        key="no2_annual", pollutant_group="NO2", parameter_code="42602",
        aqs_standard_label="NO2 Annual 1971", method="annual_stat",
        stat_column="arithmetic_mean", default_year_form="most_recent",
        display_name="NO2 Annual (1971)", unit_hint="ppb",
    ),
    Standard(
        key="ozone_8hr", pollutant_group="Ozone", parameter_code="44201",
        aqs_standard_label="Ozone 8-hour 2015", method="annual_stat",
        stat_column="4th_max_value", default_year_form="average",
        display_name="Ozone 8-hour (2015)", unit_hint="ppm",
    ),
    Standard(
        key="so2_1hr", pollutant_group="SO2", parameter_code="42401",
        aqs_standard_label="SO2 1-hour 2010", method="annual_stat",
        stat_column="99th_percentile", default_year_form="average",
        display_name="SO2 1-hour (2010)", unit_hint="ppb",
    ),
    Standard(
        key="so2_3hr", pollutant_group="SO2", parameter_code="42401",
        aqs_standard_label="SO2 3-hour 1971", method="annual_stat",
        stat_column="second_max_value", default_year_form="most_recent",
        display_name="SO2 3-hour (1971)", unit_hint="ppb",
    ),
    Standard(
        key="so2_24hr", pollutant_group="SO2", parameter_code="42401",
        aqs_standard_label="SO2 24-hour 1971", method="annual_stat",
        stat_column="second_max_value", default_year_form="most_recent",
        display_name="SO2 24-hour (1971)", unit_hint="ppb",
    ),
    Standard(
        key="so2_annual", pollutant_group="SO2", parameter_code="42401",
        aqs_standard_label="SO2 Annual 1971", method="annual_stat",
        stat_column="arithmetic_mean", default_year_form="most_recent",
        display_name="SO2 Annual (1971)", unit_hint="ppb",
    ),
    Standard(
        key="pm25_24hr_annual_lookup", pollutant_group="PM2.5", parameter_code="88101",
        aqs_standard_label="PM25 24-hour 2024", method="annual_stat",
        stat_column="98th_percentile", default_year_form="average",
        display_name="PM2.5 24-hour (annual-file 98th percentile)", unit_hint="ug/m3",
    ),
    Standard(
        key="pm25_annual", pollutant_group="PM2.5", parameter_code="88101",
        aqs_standard_label="PM25 Annual 2024", method="annual_stat",
        stat_column="arithmetic_mean", default_year_form="average",
        display_name="PM2.5 Annual", unit_hint="ug/m3",
    ),
    Standard(
        key="pm10_24hr_annual_lookup", pollutant_group="PM10", parameter_code="81102",
        aqs_standard_label="PM10 24-hour 2006", method="annual_stat",
        stat_column="second_max_value", default_year_form="most_recent",
        display_name="PM10 24-hour (annual-file 2nd max, quick view)", unit_hint="ug/m3",
    ),
    Standard(
        # NOTE: the source workbook's PM2.5 Profile tab hardcodes the *daily*
        # file lookup to "PM25 24-hour 2012", not "...2024" (which is what the
        # annual-file lookups above use). Both labels currently exist
        # side-by-side in EPA's real annual_conc_by_monitor files (confirmed
        # against a live 2023 file) since the 24-hour standard's level (35
        # ug/m3) didn't change in the 2024 PM2.5 rule -- only the Annual
        # standard did. We replicate the workbook's exact daily-file label
        # here rather than guessing; flagged to the user as an open item.
        key="pm25_seasonal_profile", pollutant_group="PM2.5", parameter_code="88101",
        aqs_standard_label="PM25 24-hour 2012", method="pm25_seasonal_profile",
        daily_file_code="88101",
        display_name="PM2.5 Seasonal Background Profile (3-yr, daily-based)", unit_hint="ug/m3",
    ),
    Standard(
        key="pm10_multiyear", pollutant_group="PM10", parameter_code="81102",
        aqs_standard_label="PM10 24-hour 2006", method="pm10_multiyear_4th_high",
        daily_file_code="81102",
        display_name="PM10 24-hour Design Value (3-yr 4th-highest, daily-based)", unit_hint="ug/m3",
    ),
    Standard(
        key="lead_rolling", pollutant_group="Lead", parameter_code="14129",
        aqs_standard_label="Pb 3-Month 2008", method="lead_rolling_3mo",
        daily_file_code="LEAD",
        display_name="Lead (Pb) Rolling 3-Month Design Value", unit_hint="ug/m3",
    ),
]

POLLUTANT_GROUPS = sorted({s.pollutant_group for s in STANDARDS})

STANDARDS_BY_KEY = {s.key: s for s in STANDARDS}

# EPA's annual_conc_by_monitor column names -> the short keys used above.
ANNUAL_STAT_COLUMNS = {
    "arithmetic_mean": "Arithmetic Mean",
    "second_max_value": "2nd Max Value",
    "4th_max_value": "4th Max Value",
    "98th_percentile": "98th Percentile",
    "99th_percentile": "99th Percentile",
}
