"""
Richmond Metro Census Comparison
Pulls ACS 5-Year data for Richmond City, Henrico, Chesterfield, and Hanover
and outputs a publish-ready comparison table (Markdown + CSV).

Usage:
    export CENSUS_API_KEY="your_census_api_key"
    python scripts/richmond_census_pull.py

Requires: pip install requests
"""

import csv
import os
import sys

import requests

API_KEY = os.environ.get("CENSUS_API_KEY", "")
if not API_KEY:
    sys.exit("Set CENSUS_API_KEY environment variable first.")

YEAR = 2023          # latest ACS 5-year release
BASELINE_YEAR = 2018  # for 5-year change comparison

STATE = "51"  # Virginia
LOCALITIES = {
    "760": "Richmond City",
    "087": "Henrico County",
    "041": "Chesterfield County",
    "085": "Hanover County",
}

# Detailed-table variables
DETAIL_VARS = {
    "B01003_001E": "Population",
    "B01002_001E": "Median Age",
    "B19013_001E": "Median Household Income",
    "B25077_001E": "Median Home Value",
    "B25064_001E": "Median Gross Rent",
    "B25003_001E": "_occupied_total",
    "B25003_002E": "_owner_occupied",
}

# Data-profile variables (separate endpoint)
PROFILE_VARS = {
    "DP03_0025E": "Mean Commute (min)",
}


def fetch(year, dataset, variables):
    """Fetch variables for all four localities. Returns {fips: {var: value}}."""
    url = f"https://api.census.gov/data/{year}/{dataset}"
    params = {
        "get": ",".join(variables),
        "for": f"county:{','.join(LOCALITIES)}",
        "in": f"state:{STATE}",
        "key": API_KEY,
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    rows = r.json()
    header = rows[0]
    out = {}
    for row in rows[1:]:
        rec = dict(zip(header, row))
        out[rec["county"]] = {v: rec.get(v) for v in variables}
    return out


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def money(x):
    return f"${x:,.0f}" if x is not None else "—"


def main():
    print(f"Pulling ACS 5-Year data ({YEAR}) ...")
    detail = fetch(YEAR, "acs/acs5", list(DETAIL_VARS))
    profile = fetch(YEAR, "acs/acs5/profile", list(PROFILE_VARS))
    print(f"Pulling {BASELINE_YEAR} baseline for home-value change ...")
    baseline = fetch(BASELINE_YEAR, "acs/acs5", ["B25077_001E"])

    results = []
    for fips, name in LOCALITIES.items():
        d = detail.get(fips, {})
        p = profile.get(fips, {})
        b = baseline.get(fips, {})

        pop = num(d.get("B01003_001E"))
        age = num(d.get("B01002_001E"))
        income = num(d.get("B19013_001E"))
        home_value = num(d.get("B25077_001E"))
        rent = num(d.get("B25064_001E"))
        occ_total = num(d.get("B25003_001E"))
        owner = num(d.get("B25003_002E"))
        commute = num(p.get("DP03_0025E"))
        hv_2018 = num(b.get("B25077_001E"))

        own_rate = (owner / occ_total * 100) if owner and occ_total else None
        hv_change = ((home_value - hv_2018) / hv_2018 * 100) if home_value and hv_2018 else None

        results.append({
            "Locality": name,
            "Population": f"{pop:,.0f}" if pop is not None else "—",
            "Median Age": f"{age:.1f}" if age is not None else "—",
            "Median HH Income": money(income),
            "Median Home Value": money(home_value),
            f"Home Value Change {BASELINE_YEAR}-{YEAR}": f"{hv_change:+.1f}%" if hv_change is not None else "—",
            "Median Gross Rent": money(rent),
            "Homeownership Rate": f"{own_rate:.1f}%" if own_rate is not None else "—",
            "Mean Commute": f"{commute:.1f} min" if commute is not None else "—",
        })

    cols = list(results[0].keys())

    # CSV
    with open("richmond_metro_comparison.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(results)

    # Markdown table
    lines = ["| " + " | ".join(cols) + " |",
             "|" + "|".join(["---"] * len(cols)) + "|"]
    for r in results:
        lines.append("| " + " | ".join(r[c] for c in cols) + " |")
    md = "\n".join(lines)

    with open("richmond_metro_comparison.md", "w") as f:
        f.write(f"# Greater Richmond Market Comparison (ACS {YEAR} 5-Year)\n\n")
        f.write(md + "\n\n")
        f.write("Source: U.S. Census Bureau, American Community Survey 5-Year Estimates.\n")

    print("\n" + md)
    print("\nSaved: richmond_metro_comparison.csv, richmond_metro_comparison.md")


if __name__ == "__main__":
    main()
