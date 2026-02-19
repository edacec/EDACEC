# EDACEC

EDACEC (Emergent Dynamics Analysis & Civil Equilibrium Calculation) is a deterministic volatility measurement instrument.

It measures escalation signals in headlines using a fixed HESM dictionary and a locked scoring formula.

Measurement is invariant.
Interpretation is separate.

---

## Architecture

EDACEC is intentionally two-layered:

1. measurement_locked/
   - Deterministic scoring engine
   - Exact string matching
   - Fixed formula: VI = 0.020 + (0.027 × k)
   - Produces JSONL outputs

2. interface_playground/
   - Reads measurement outputs
   - Visualizes and summarizes data
   - Does not modify measurement

---

## Quickstart

### Install dependencies

python3 -m pip install -r requirements.txt

### Run measurement (creates dated output)

cd measurement_locked
python3 edacec_v1_08.py --spec EDACEC_v1.08_spec.json --in runs/inputs/headlines.jsonl --out "runs/outputs/$(date +%F)_edacec_output.jsonl"

### Run instrument (local dashboard)

cd ../interface_playground
python3 -m streamlit run instrument_app.py

---

## Output Format

Each headline produces a JSON object including:

- component scores (S, E, I, A)
- matched tokens
- k total
- Volatility Index (VI)

Outputs are stored as JSONL in:

measurement_locked/runs/outputs/

---

## Principles

- Exact match only
- No semantic inference
- No embeddings
- Versioned specification
- Measurement does not interpret

EDACEC is a measurement tool.
Visualization layers are instruments built on top of it.
