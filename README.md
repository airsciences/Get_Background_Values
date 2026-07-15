# EPA Background Value Estimator

A Flask web app that reimplements the calculations from
`AirSci Get Background Values_v1.10.xlsm`, pulling EPA air monitoring data
live from EPA's pre-generated AQS data files instead of manually-maintained
local CSV copies.

UNTESTED AS OF 7/15/2026

## What this replaces

The source workbook's VBA macros only import EPA CSVs into worksheets; the
actual background-level logic lives in spreadsheet formulas across the
Stations, Summary, PM2.5 Profile, and PM10 Multiyear tabs. This app
reimplements that formula logic in Python, with EPA files downloaded and
cached on demand (`data_cache/`) instead of requiring someone to manually
keep local copies current.

## How it works (3 steps, matching the workbook's own workflow)

1. **Facility + radius.** Enter facility latitude/longitude and a search
   radius (km) for each pollutant group you want (CO, NO2, Ozone, PM10,
   PM2.5, SO2, Lead). Leave a pollutant blank to skip it.
2. **Pick a representative monitor.** For each NAAQS standard, the app
   finds candidate monitors within the radius (true haversine circle, not
   the workbook's lat/long bounding-box approximation) that report that
   exact standard, and shows distance / observation count / completeness
   for each. **You pick one monitor per standard** -- this mirrors the
   workbook's design: background levels come from a single, human-chosen
   representative monitor, not an automatic multi-monitor average. Data
   must still be reviewed for representativeness, completeness, and
   validity, same as the original tool's ReadMe instructs.
3. **Results.** The app computes the background value for each standard
   from your chosen monitor's data.

## Pollutant standards and statistics implemented

| Standard | Statistic | Source |
|---|---|---|
| CO 1-hr / 8-hr (1971) | 2nd-highest value, most recent year | annual file |
| NO2 1-hr (2010) | 98th percentile, 3-yr average | annual file |
| NO2 Annual (1971) | Arithmetic mean, most recent year | annual file |
| Ozone 8-hr (2015) | 4th-highest daily max, 3-yr average | annual file |
| SO2 1-hr (2010) | 99th percentile, 3-yr average | annual file |
| SO2 3-hr / 24-hr / Annual (1971) | 2nd-highest (short-term) or mean (annual), most recent year | annual file |
| PM10 24-hr (2006), quick view | 2nd-highest value, most recent year | annual file |
| PM10 24-hr (2006), design value | Pooled 4th-highest 24-hr value across 3 years (top-4-per-year, pooled) | **daily** file |
| PM2.5 24-hr, quick view | 98th percentile, 3-yr average | annual file |
| PM2.5 Annual | Arithmetic mean, 3-yr average | annual file |
| PM2.5 Seasonal Background Profile | Per EPA's 2024 background-concentration guidance: 98th-percentile cutoff per monitoring year (Dec-Nov), then max of days below that cutoff per season (Winter/Spring/Summer/Fall), averaged over 3 years | **daily** file |
| Lead (Pb) | Maximum rolling 3-month arithmetic mean over 3 years (40 CFR Part 50 Appendix R) | **daily** file |

Every row above except Lead was verified against the workbook's actual
formulas. **Lead has no equivalent calculation anywhere in the source
workbook** (it only downloads daily Lead data, never computes a value from
it) -- the Lead calculator here is new logic built from the NAAQS Pb
methodology, not a workbook reimplementation, and should be treated with
more skepticism until checked against a known real-world example.

## Known deviations / open items

- **Distance filter: haversine circle, not a bounding box.** The workbook
  approximates a radius filter with a rectangular lat/long box
  (`center ± radius_km / km_per_degree`), which is not a true circle. This
  app uses actual great-circle (haversine) distance instead, per an
  explicit decision to prioritize correctness over exact numerical parity
  with the workbook. Candidate lists (and therefore which monitors are even
  offered) may differ slightly near a facility's box corners versus its
  circle edge.
- **PM2.5 24-hour standard label mismatch.** EPA's annual files carry both
  `"PM25 24-hour 2012"` and `"PM25 24-hour 2024"` as valid `Pollutant
  Standard` values for the same 35 ug/m3 standard (only the PM2.5 *Annual*
  standard actually changed in the 2024 rule). The workbook's Summary/
  Stations tabs use `"...2024"` for annual-file lookups but its PM2.5
  Profile tab hardcodes `"...2012"` for the daily-file-based seasonal
  calculation. This app replicates that exact split rather than guessing
  which is "right" -- worth spot-checking against a live EPA file if
  results look unexpected.
- **Lead's exact `Pollutant Standard` label is unconfirmed** (assumed
  `"Pb 3-Month 2008"` in `epa_background/pollutants.py`) -- no local Lead
  daily file was available to verify this against real EPA data.

## Validating against a past report

Enter the same facility lat/long and per-pollutant radii used in a past
AirSci report, pick the same monitor(s) the workbook run used, and compare
the resulting values (allowing for the haversine-vs-box difference in which
monitors show up as candidates, and for rounding).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

Then open http://127.0.0.1:5000/.

The first run for any given year will download and cache EPA's nationwide
annual/daily files (tens of MB each) into `data_cache/`; subsequent runs
reuse the cache. If EPA hasn't published a requested year yet (the site
updates twice a year, per the workbook's own ReadMe), the app will report
that year as unavailable rather than erroring silently.
