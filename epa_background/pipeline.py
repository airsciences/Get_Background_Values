"""Orchestrates the two-step workflow: find candidates, then compute results
for whichever monitor the user picked per standard.
"""

from dataclasses import dataclass

from . import annual_stats, lead, pm10_multiyear, pm25_profile
from .candidates import MonitorCandidate, find_candidates
from .downloader import EPADataUnavailable
from .pollutants import STANDARDS, STANDARDS_BY_KEY


def three_year_window(latest_year: int) -> list[int]:
    return [latest_year - 2, latest_year - 1, latest_year]


def get_candidates_for_all_standards(
    facility_lat: float,
    facility_lon: float,
    radius_by_group: dict[str, float],
    reference_year: int,
) -> dict[str, list[MonitorCandidate]]:
    """radius_by_group keys are Standard.pollutant_group values (CO, NO2, ...)."""
    results: dict[str, list[MonitorCandidate]] = {}
    for standard in STANDARDS:
        radius = radius_by_group.get(standard.pollutant_group)
        if not radius:
            results[standard.key] = []
            continue
        try:
            results[standard.key] = find_candidates(
                facility_lat, facility_lon, radius, standard.aqs_standard_label, reference_year
            )
        except EPADataUnavailable:
            results[standard.key] = []
    return results


@dataclass
class StandardResult:
    standard_key: str
    display_name: str
    unit_hint: str
    method: str
    site_name: str | None
    error: str | None
    detail: object  # AnnualStatResult | PM25ProfileResult | PM10MultiyearResult | LeadResult


def compute_all_results(selections: dict[str, str], reference_year: int) -> list[StandardResult]:
    """selections maps standard_key -> chosen site_name (skip keys the user left blank)."""
    years = three_year_window(reference_year)
    out: list[StandardResult] = []

    for standard in STANDARDS:
        site_name = selections.get(standard.key)
        if not site_name:
            out.append(StandardResult(standard.key, standard.display_name, standard.unit_hint, standard.method, None, "No monitor selected", None))
            continue

        try:
            if standard.method == "annual_stat":
                detail = annual_stats.compute_annual_stat(standard, site_name, years)
            elif standard.method == "pm25_seasonal_profile":
                detail = pm25_profile.compute_pm25_profile(standard, site_name, years)
            elif standard.method == "pm10_multiyear_4th_high":
                detail = pm10_multiyear.compute_pm10_multiyear(standard, site_name, years)
            elif standard.method == "lead_rolling_3mo":
                detail = lead.compute_lead_design_value(standard, site_name, years)
            else:
                raise ValueError(f"Unknown method {standard.method}")
            out.append(StandardResult(standard.key, standard.display_name, standard.unit_hint, standard.method, site_name, None, detail))
        except EPADataUnavailable as exc:
            out.append(StandardResult(standard.key, standard.display_name, standard.unit_hint, standard.method, site_name, str(exc), None))

    return out
