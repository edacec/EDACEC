import json
from pathlib import Path
from statistics import mean

OUTDIR = Path("../measurement_locked/runs/outputs")

def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def main():
    files = sorted(OUTDIR.glob("*_edacec_output.jsonl"))
    if len(files) < 2:
        print("Need 2+ dated output files for trend.")
        print("Current files:")
        for f in sorted(OUTDIR.glob("*.jsonl")):
            print(" -", f.name)
        return

    print(f"Found {len(files)} dated runs.\n")

    rows = []
    for f in files:
        # filename format: YYYY-MM-DD_edacec_output.jsonl
        date = f.name.split("_")[0]
        data = load_jsonl(f)

        vis = [r["vi"] for r in data]
        ks = [r["hesm"]["k_total"] for r in data]

        # component averages
        s_vals = [r["hesm"]["scores"]["structural"] for r in data]
        e_vals = [r["hesm"]["scores"]["emotional"] for r in data]
        i_vals = [r["hesm"]["scores"]["irreversibility"] for r in data]
        a_vals = [r["hesm"]["scores"]["agenda"] for r in data]

        rows.append({
            "date": date,
            "n_headlines": len(data),
            "avg_vi": round(mean(vis), 3),
            "avg_k": round(mean(ks), 2),
            "avg_S": round(mean(s_vals), 2),
            "avg_E": round(mean(e_vals), 2),
            "avg_I": round(mean(i_vals), 2),
            "avg_A": round(mean(a_vals), 2),
            "max_vi": round(max(vis), 3),
        })

    # print table
    print("DATE        n  avg_VI  avg_k  avg_S  avg_E  avg_I  avg_A  max_VI")
    print("----------  -  ------  -----  -----  -----  -----  -----  ------")
    for r in rows:
        print(f"{r['date']}  "
              f"{r['n_headlines']:>1}  "
              f"{r['avg_vi']:>6}  "
              f"{r['avg_k']:>5}  "
              f"{r['avg_S']:>5}  "
              f"{r['avg_E']:>5}  "
              f"{r['avg_I']:>5}  "
              f"{r['avg_A']:>5}  "
              f"{r['max_vi']:>6}")

    print("\nNote: trend is computed from locked measurement outputs only.")

if __name__ == "__main__":
    main()



