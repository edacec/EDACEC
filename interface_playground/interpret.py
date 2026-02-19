import json
from pathlib import Path

INPUT = Path("../measurement_locked/runs/outputs/edacec_output.jsonl")

def main():
    if not INPUT.exists():
        print("No measurement output found.")
        print("Run measurement first from ../measurement_locked:")
        print("python3 edacec_v1_08.py --spec EDACEC_v1.08_spec.json --in runs/inputs/headlines.jsonl --out runs/outputs/edacec_output.jsonl")
        return

    rows = [json.loads(line) for line in INPUT.read_text(encoding="utf-8").splitlines() if line.strip()]
    print(f"Loaded {len(rows)} scored headlines from locked measurement.\n")

    rows.sort(key=lambda r: r["hesm"]["k_total"], reverse=True)

    for i, r in enumerate(rows, start=1):
        meta = r.get("meta", {})
        src = meta.get("source", "Unknown")
        ts = meta.get("timestamp", "Unknown")
        k = r["hesm"]["k_total"]
        vi = r["vi"]
        s = r["hesm"]["scores"]
        print(f"[{i}] {src} — {ts}")
        print(f"Headline: {r['headline']}")
        print(f"HESM: S={s['structural']} E={s['emotional']} I={s['irreversibility']} A={s['agenda']} | k={k} | VI={vi}")
        print(f"Matches: {r['hesm']['matches']}")
        print("-" * 60)

if __name__ == "__main__":
    main()
