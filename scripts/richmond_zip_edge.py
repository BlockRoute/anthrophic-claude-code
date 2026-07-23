"""
Richmond Metro ZIP-Level Market Edge
Builds a per-ZIP "Market Heat Index" and opportunity screen for the Richmond, VA
metro from Redfin's public data lake (zip_code_market_tracker).

Input:  va_zip_tracker.tsv (Redfin ZIP tracker filtered to VA rows)
Output: richmond_zip_edge.csv, richmond_zip_edge.json

Method:
  - Restrict to Richmond, VA metro ZIPs, "All Residential" property type.
  - Smooth monthly noise with 3-month rolling averages.
  - Heat Index (0-100) = mean of percentile ranks across five demand signals:
      fast sales (low DOM), sale-to-list ratio, % sold above list,
      low months of supply, % off-market within two weeks.
  - Momentum = change in Heat Index vs. 12 months earlier (cooling/heating).
  - Value Gap = 5-yr price appreciation vs. metro median (laggards with high
    current heat = likely catch-up appreciation).
"""

import json
import sys

import pandas as pd

SRC = sys.argv[1] if len(sys.argv) > 1 else "va_zip_tracker.tsv"

ZIP_NAMES = {
    "23005": "Ashland (Hanover)", "23009": "Aylett (King William)",
    "23015": "Beaverdam (Hanover)", "23047": "Doswell (Hanover)",
    "23059": "Glen Allen/Wyndham (Henrico)", "23060": "Glen Allen (Henrico)",
    "23063": "Goochland", "23069": "Hanover Courthouse",
    "23075": "Highland Springs (Henrico)", "23102": "Maidens (Goochland)",
    "23103": "Manakin-Sabot (Goochland)", "23111": "Mechanicsville (Hanover)",
    "23112": "Midlothian/Brandermill (Chesterfield)",
    "23113": "Midlothian/Salisbury (Chesterfield)",
    "23114": "Midlothian/Charter Colony (Chesterfield)",
    "23116": "Mechanicsville/Atlee (Hanover)", "23120": "Moseley (Chesterfield)",
    "23124": "New Kent", "23139": "Powhatan", "23140": "Providence Forge (New Kent)",
    "23141": "Quinton (New Kent)", "23150": "Sandston (Henrico)",
    "23219": "Downtown Richmond", "23220": "The Fan/VCU (Richmond)",
    "23221": "Museum District/Carytown (Richmond)",
    "23222": "Northside/Highland Park (Richmond)",
    "23223": "Church Hill/East End (Richmond)",
    "23224": "Manchester/Southside (Richmond)",
    "23225": "Westover Hills/Forest Hill (Richmond)",
    "23226": "Libbie-Grove/Westhampton (Richmond)",
    "23227": "Lakeside/Bellevue (Henrico)", "23228": "Glenside/Lakeside (Henrico)",
    "23229": "Tuckahoe/River Road (Henrico)",
    "23230": "Scott's Addition/Willow Lawn (Richmond)",
    "23231": "Varina/Fulton (Henrico)", "23233": "Short Pump/Innsbrook (Henrico)",
    "23234": "Bensley/Meadowbrook (Chesterfield)", "23235": "Bon Air (Chesterfield)",
    "23236": "N. Chesterfield/Robious", "23237": "Chester North (Chesterfield)",
    "23238": "Gayton/Tuckahoe West (Henrico)", "23294": "Innsbrook/West End (Henrico)",
    "23803": "Petersburg West", "23805": "Petersburg South",
    "23830": "Carson (Prince George)", "23831": "Chester (Chesterfield)",
    "23832": "Chesterfield Courthouse", "23834": "Colonial Heights",
    "23836": "Chester/Enon (Chesterfield)", "23838": "Winterpock (Chesterfield)",
    "23841": "Dinwiddie", "23842": "Disputanta (Prince George)",
    "23860": "Hopewell", "23875": "Prince George",
}

df = pd.read_csv(SRC, sep="\t", quotechar='"')
df.columns = [c.strip('"').lower() for c in df.columns]

for col in df.select_dtypes("object"):
    df[col] = df[col].str.strip('"')

metro = df[
    (df["parent_metro_region"] == "Richmond, VA")
    & (df["property_type"] == "All Residential")
].copy()

metro["period_begin"] = pd.to_datetime(metro["period_begin"])
metro["zip"] = metro["region"].str.extract(r"(\d{5})")

num_cols = [
    "median_sale_price", "median_ppsf", "median_dom", "avg_sale_to_list",
    "sold_above_list", "months_of_supply", "off_market_in_two_weeks",
    "homes_sold", "inventory", "new_listings", "price_drops",
    "median_sale_price_yoy",
]
for c in num_cols:
    metro[c] = pd.to_numeric(metro[c], errors="coerce")

metro = metro.sort_values(["zip", "period_begin"])

# 3-month rolling means per ZIP to tame small-sample monthly noise
roll_cols = [
    "median_sale_price", "median_ppsf", "median_dom", "avg_sale_to_list",
    "sold_above_list", "months_of_supply", "off_market_in_two_weeks",
    "homes_sold", "inventory", "price_drops",
]
for c in roll_cols:
    metro[f"{c}_3m"] = metro.groupby("zip")[c].transform(
        lambda s: s.rolling(3, min_periods=2).mean()
    )

latest_period = metro["period_begin"].max()


def heat_index(snapshot):
    """Percentile-rank composite of four demand signals, 0-100.

    (Redfin does not publish months_of_supply or price_drops at ZIP level.)
    """
    parts = pd.DataFrame({
        "dom": -snapshot["median_dom_3m"],
        "stl": snapshot["avg_sale_to_list_3m"],
        "abv": snapshot["sold_above_list_3m"],
        "fast": snapshot["off_market_in_two_weeks_3m"],
    })
    ranks = parts.rank(pct=True)
    return (ranks.mean(axis=1, skipna=True) * 100).round(1)


def snapshot_at(period):
    snap = metro[metro["period_begin"] == period].set_index("zip")
    snap = snap[snap["homes_sold_3m"] >= 3]  # drop ZIPs too thin to score
    snap = snap.copy()
    snap["heat"] = heat_index(snap)
    return snap


now = snapshot_at(latest_period)
year_ago = snapshot_at(latest_period - pd.DateOffset(years=1))

# 5-year appreciation per ZIP (3m-smoothed price then vs now)
five_ago = metro[metro["period_begin"] == latest_period - pd.DateOffset(years=5)]
five_ago = five_ago.set_index("zip")["median_sale_price_3m"]
appreciation_5y = (now["median_sale_price_3m"] / five_ago - 1) * 100

out = pd.DataFrame({
    "zip": now.index,
    "area": [ZIP_NAMES.get(z, "") for z in now.index],
    "median_sale_price": now["median_sale_price_3m"].round(0).values,
    "price_yoy_pct": now["median_sale_price_yoy"].mul(100).round(1).values,
    "median_ppsf": now["median_ppsf_3m"].round(0).values,
    "median_dom": now["median_dom_3m"].round(0).values,
    "sale_to_list_pct": now["avg_sale_to_list_3m"].mul(100).round(1).values,
    "sold_above_list_pct": now["sold_above_list_3m"].mul(100).round(1).values,
    "off_market_2wk_pct": now["off_market_in_two_weeks_3m"].mul(100).round(1).values,
    "homes_sold_3m_avg": now["homes_sold_3m"].round(1).values,
    "inventory": now["inventory_3m"].round(0).values,
    "appreciation_5y_pct": appreciation_5y.reindex(now.index).round(1).values,
    "heat_index": now["heat"].values,
    "heat_index_year_ago": year_ago["heat"].reindex(now.index).values,
}).reset_index(drop=True)

# Thin-sample ZIPs can't support confident conclusions — label them
out["volume_tier"] = pd.cut(
    out["homes_sold_3m_avg"], [0, 10, 30, float("inf")],
    labels=["thin (<10 sales/mo)", "moderate", "high volume"],
)

out["heat_momentum"] = (out["heat_index"] - out["heat_index_year_ago"]).round(1)

metro_appr = out["appreciation_5y_pct"].median()
out["value_gap_pct"] = (out["appreciation_5y_pct"] - metro_appr).round(1)

# Opportunity flags
out["flag"] = ""
out.loc[(out["heat_index"] >= 70) & (out["value_gap_pct"] < 0), "flag"] = "CATCH-UP BUY"
out.loc[(out["heat_momentum"] <= -15), "flag"] = "BUYER LEVERAGE"
out.loc[(out["heat_index"] >= 80) & (out["heat_momentum"] > 0), "flag"] = "LISTING GOLDMINE"

out = out.sort_values("heat_index", ascending=False).reset_index(drop=True)

out.to_csv("richmond_zip_edge.csv", index=False)

# Locality-level monthly trends for the four core jurisdictions (county tracker)
trends = {}
try:
    cty = pd.read_csv("va_county_tracker.tsv", sep="\t", quotechar='"')
    cty.columns = [c.strip('"').lower() for c in cty.columns]
    for col in cty.select_dtypes(include=["object", "str"]):
        cty[col] = cty[col].str.strip('"')
    # NB: Redfin labels the independent city "Richmond City County, VA";
    # "Richmond County, VA" is the unrelated Northern Neck county.
    core = {
        "Richmond City County, VA": "Richmond City",
        "Henrico County, VA": "Henrico",
        "Chesterfield County, VA": "Chesterfield",
        "Hanover County, VA": "Hanover",
    }
    cty = cty[
        cty["region"].isin(core) & (cty["property_type"] == "All Residential")
    ].copy()
    cty["period_begin"] = pd.to_datetime(cty["period_begin"])
    cty = cty[cty["period_begin"] >= "2019-01-01"].sort_values("period_begin")
    for c in ["median_sale_price", "median_dom", "inventory", "months_of_supply"]:
        cty[c] = pd.to_numeric(cty[c], errors="coerce")
    for region, label in core.items():
        sub = cty[cty["region"] == region]
        trends[label] = {
            "months": [str(d.date()) for d in sub["period_begin"]],
            "median_sale_price": sub["median_sale_price"].tolist(),
            "median_dom": sub["median_dom"].tolist(),
            "inventory": sub["inventory"].tolist(),
            "months_of_supply": sub["months_of_supply"].tolist(),
        }
except FileNotFoundError:
    pass

with open("richmond_zip_edge.json", "w") as f:
    json.dump({
        "as_of": str(latest_period.date()),
        "metro_median_5y_appreciation_pct": round(float(metro_appr), 1),
        "zips": out.where(pd.notna(out), None).to_dict(orient="records"),
        "locality_trends": trends,
    }, f, indent=1)

print(f"As of {latest_period.date()} — {len(out)} scored ZIPs")
print(out.to_string(index=False))
