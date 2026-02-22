#!/usr/bin/env python3
"""
EDACEC v1.08 — Minimal Deterministic Engine (no LLM required)

- Exact-match keyword scoring (case-insensitive)
- Headline text only
- No embeddings, no semantic inference
- Reproducible output schema

Scoring:
- For each component C in {structural, emotional, irreversibility, agenda}:
    matched_count_C = number of UNIQUE keywords from C present in headline tokens
    score_C = min(component_max_C, matched_count_C)
- k = score_structural + score_emotional + score_irreversibility + score_agenda
- VI = 0.020 + (0.027 * k)

Tokenization (deterministic):
- lowercase
- replace hyphens with spaces
- extract word tokens: alnum + internal apostrophes
- split by regex
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Tuple, Any


_WORD_RE = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?", re.IGNORECASE)

def tokenize(text: str) -> List[str]:
    text = text.lower().replace("-", " ")
    return _WORD_RE.findall(text)


@dataclass(frozen=True)
class ComponentSpec:
    name: str
    max_score: int
    keywords: Tuple[str, ...]  # lowercase


@dataclass(frozen=True)
class EDACECSpec:
    version: str
    components: Dict[str, ComponentSpec]

    @staticmethod
    def from_json(obj: Dict[str, Any]) -> "EDACECSpec":
        version = str(obj.get("version", "unknown"))
        d = obj["dictionary"]

        def comp(key: str) -> ComponentSpec:
            comp_obj = d[key]
            keywords = tuple(k.lower() for k in comp_obj["keywords"])
            return ComponentSpec(name=key, max_score=int(comp_obj["max_score"]), keywords=keywords)

        return EDACECSpec(
            version=version,
            components={
                "structural": comp("structural"),
                "emotional": comp("emotional"),
                "irreversibility": comp("irreversibility"),
                "agenda": comp("agenda"),
            },
        )


def score_headline(headline: str, spec: EDACECSpec) -> Dict[str, Any]:
    tokens = tokenize(headline)
    token_set = set(tokens)

    matches: Dict[str, List[str]] = {}
    scores: Dict[str, int] = {}

    for comp_name, comp_spec in spec.components.items():
        matched = sorted([kw for kw in comp_spec.keywords if kw in token_set])
        scores[comp_name] = min(comp_spec.max_score, len(matched))
        matches[comp_name] = matched

    k = int(sum(scores.values()))
    vi_raw = 0.020 + (0.027 * k)
    vi = round(vi_raw, 3)

    return {
        "edacec_version": spec.version,
        "headline": headline,
        "hesm": {
            "scores": scores,
            "matches": matches,
            "k_total": k,
        },
        "vi": vi,
        "vi_raw": vi_raw,
    }


def parse_headlines_jsonl(path: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON on line {i}: {e}") from e
            if "headline" not in obj:
                raise ValueError(f"Missing 'headline' on line {i}")
            items.append(obj)
    return items


def write_jsonl(path: str, rows: List[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main(argv: List[str]) -> int:
    p = argparse.ArgumentParser(description="EDACEC v1.08 minimal deterministic engine")
    p.add_argument("--spec", required=True, help="Path to EDACEC spec JSON")
    p.add_argument("--in", dest="in_path", required=True, help="Input JSONL file (requires 'headline')")
    p.add_argument("--out", dest="out_path", required=True, help="Output JSONL file path")
    args = p.parse_args(argv)

    with open(args.spec, "r", encoding="utf-8") as f:
        spec_obj = json.load(f)
    spec = EDACECSpec.from_json(spec_obj)

    items = parse_headlines_jsonl(args.in_path)

    results: List[Dict[str, Any]] = []
    run_utc = datetime.utcnow().isoformat(timespec="seconds") + "Z"

    for item in items:
        scored = score_headline(item["headline"], spec)
        meta = {k: v for k, v in item.items() if k != "headline"}
        scored["meta"] = meta
        scored["run_utc"] = run_utc
        results.append(scored)

    write_jsonl(args.out_path, results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
