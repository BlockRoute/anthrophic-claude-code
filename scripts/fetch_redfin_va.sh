#!/usr/bin/env bash
# Streams Redfin's public market-tracker files and keeps only Virginia rows.
# The national ZIP file is ~1 GB uncompressed; this never stores it in full.
# Redfin refreshes the feed monthly — rerun, then run richmond_zip_edge.py.
set -euo pipefail

BASE="https://redfin-public-data.s3.us-west-2.amazonaws.com/redfin_market_tracker"

filter_va() {
  zcat 2>/dev/null | awk -F'\t' 'NR==1{print; next} $0 ~ /\t"VA"\t/{print}'
}

curl -s "$BASE/zip_code_market_tracker.tsv000.gz" | filter_va > va_zip_tracker.tsv
curl -s "$BASE/county_market_tracker.tsv000.gz" | filter_va > va_county_tracker.tsv

wc -l va_zip_tracker.tsv va_county_tracker.tsv
