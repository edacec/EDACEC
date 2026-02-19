#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/../measurement_locked"
mkdir -p runs/outputs

python3 edacec_v1_08.py \
  --spec EDACEC_v1.08_spec.json \
  --in runs/inputs/headlines.jsonl \
  --out "runs/outputs/$(date +%F)_edacec_output.jsonl"

echo "Wrote: measurement_locked/runs/outputs/$(date +%F)_edacec_output.jsonl"
