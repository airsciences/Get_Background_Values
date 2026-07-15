"""EPA Background Value Estimator -- Flask app.

Three-step flow, mirroring the workbook's Stations -> Summary workflow:
  1. GET  /              facility lat/long + per-pollutant-group radius
  2. POST /search        show candidate monitors per standard (haversine radius)
  3. POST /results       compute + display the background value per standard
                         for whichever monitor the user picked
"""

from datetime import date

from flask import Flask, render_template, request

from epa_background.downloader import EPADataUnavailable, try_latest_complete_year
from epa_background.pipeline import compute_all_results, get_candidates_for_all_standards, three_year_window
from epa_background.pollutants import POLLUTANT_GROUPS, STANDARDS

app = Flask(__name__)

KM_PER_MILE = 1.609344

# 25-mile steps up to 200, then 50-mile steps up to 500.
RADIUS_MILE_OPTIONS = list(range(25, 200 + 1, 25)) + list(range(250, 500 + 1, 50))


@app.template_filter("km_to_mi")
def km_to_mi(km: float) -> float:
    return round(km / KM_PER_MILE, 1)


def default_reference_year() -> int:
    # EPA typically finalizes the prior year's annual file by ~June.
    today = date.today()
    guess = today.year - 1 if today.month >= 6 else today.year - 2
    return guess


@app.route("/", methods=["GET"])
def index():
    return render_template(
        "index.html",
        pollutant_groups=POLLUTANT_GROUPS,
        default_year=default_reference_year(),
        radius_mile_options=RADIUS_MILE_OPTIONS,
    )


@app.route("/search", methods=["POST"])
def search():
    errors = []

    try:
        facility_lat = float(request.form["facility_lat"])
        facility_lon = float(request.form["facility_lon"])
    except (KeyError, ValueError):
        errors.append("Latitude and longitude must be numbers.")
        facility_lat = facility_lon = None

    if facility_lat is not None and not (-90 <= facility_lat <= 90):
        errors.append("Latitude must be between -90 and 90.")
    if facility_lon is not None and not (-180 <= facility_lon <= 180):
        errors.append("Longitude must be between -180 and 180.")

    try:
        reference_year = int(request.form["reference_year"])
    except (KeyError, ValueError):
        errors.append("Reference year must be a whole number.")
        reference_year = default_reference_year()

    radius_by_group = {}
    for group in POLLUTANT_GROUPS:
        raw = request.form.get(f"radius_{group}", "").strip()
        if not raw:
            continue
        try:
            radius_miles = float(raw)
        except ValueError:
            errors.append(f"Radius for {group} must be a number.")
            continue
        if radius_miles <= 0:
            errors.append(f"Radius for {group} must be greater than 0.")
            continue
        radius_by_group[group] = radius_miles * KM_PER_MILE

    if not radius_by_group:
        errors.append("Enter a radius for at least one pollutant.")

    if errors:
        return render_template("_errors.html", errors=errors), 400

    try:
        candidates_by_standard = get_candidates_for_all_standards(
            facility_lat, facility_lon, radius_by_group, reference_year
        )
    except EPADataUnavailable as exc:
        return render_template("_errors.html", errors=[str(exc)]), 400

    standards_with_candidates = [
        s for s in STANDARDS if radius_by_group.get(s.pollutant_group)
    ]

    return render_template(
        "_monitor_picker.html",
        facility_lat=facility_lat,
        facility_lon=facility_lon,
        reference_year=reference_year,
        standards=standards_with_candidates,
        candidates_by_standard=candidates_by_standard,
    )


@app.route("/results", methods=["POST"])
def results():
    reference_year = int(request.form["reference_year"])
    facility_lat = float(request.form["facility_lat"])
    facility_lon = float(request.form["facility_lon"])

    selections = {}
    for standard in STANDARDS:
        chosen = request.form.get(f"site_{standard.key}", "").strip()
        if chosen:
            selections[standard.key] = chosen

    result_rows = compute_all_results(selections, reference_year)
    years_used = three_year_window(reference_year)

    return render_template(
        "_results.html",
        facility_lat=facility_lat,
        facility_lon=facility_lon,
        years_used=years_used,
        results=result_rows,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
