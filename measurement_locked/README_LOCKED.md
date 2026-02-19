# measurement_locked (EDACEC v1.08)

This folder is the **locked measurement layer**.

- Do not edit `EDACEC_v1.08_spec.json` or `edacec_v1_08.py` unless you are bumping EDACEC version.
- This layer outputs a reproducible JSONL file for downstream interface/visualization.

## Run
From this folder:

python3 edacec_v1_08.py --spec EDACEC_v1.08_spec.json --in runs/inputs/headlines.jsonl --out runs/outputs/edacec_output.jsonl
