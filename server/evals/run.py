"""Run the eval dataset against the LangGraph and produce a markdown scorecard.

Usage:
    python -m evals.run
    python -m evals.run --limit 10
    python -m evals.run --out /data/scorecard.md
    python -m evals.run --out server/evals/last_scorecard.md
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from collections import defaultdict
from typing import Any, Dict, List

from evals.judge import judge_row
from rag.graph import build_graph

log = logging.getLogger("evals.run")

HERE = os.path.dirname(__file__)
DEFAULT_DATASET = os.path.join(HERE, "dataset.jsonl")
DEFAULT_SCORECARD = os.path.join(HERE, "last_scorecard.md")


def load_dataset(path: str) -> List[Dict[str, Any]]:
    rows: list[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def summarize(rows: List[Dict[str, Any]]) -> str:
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_cat[r["category"]].append(r)
    lines = ["# Christianity AI - Eval Scorecard\n"]
    total_pass = sum(1 for r in rows if r["judge"]["passed"])
    lines.append(
        f"**Overall**: {total_pass}/{len(rows)} passed ({(100 * total_pass / len(rows)):.1f}%)\n"
    )
    lines.append("## Per-category results\n")
    for cat, items in sorted(by_cat.items()):
        passed = sum(1 for r in items if r["judge"]["passed"])
        lines.append(f"- **{cat}**: {passed}/{len(items)} ({(100 * passed / len(items)):.0f}%)")
    lines.append("\n## Failures\n")
    failures = [r for r in rows if not r["judge"]["passed"]]
    if not failures:
        lines.append("None - all evals passed.")
    else:
        for r in failures:
            lines.append(f"### {r['id']} ({r['category']})")
            lines.append(f"- Prompt: `{r['prompt']}`")
            hard = r["judge"].get("hard_notes") or [
                n for n in r["judge"]["notes"] if "soft" not in n.lower()
            ]
            lines.append(f"- Hard failures: {hard}")
            soft = r["judge"].get("soft_notes") or []
            if soft:
                lines.append(f"- Soft notes: {soft}")
            lines.append(f"- Refused: {r['judge']['refused']}")
            lines.append(f"- Citations verified: {r['judge']['citations_verified']}")
            preview = (r.get("response") or "")[:300].replace("\n", " ")
            lines.append(f"- Response preview: {preview}\n")
    lines.append("\n## Soft notes (informational)\n")
    soft_all: dict[str, int] = defaultdict(int)
    for r in rows:
        for n in r["judge"].get("soft_notes") or []:
            soft_all[n] += 1
    if not soft_all:
        lines.append("None.")
    else:
        for n, c in sorted(soft_all.items(), key=lambda x: -x[1]):
            lines.append(f"- {n}: {c}")
    return "\n".join(lines) + "\n"


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s :: %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", default=DEFAULT_DATASET)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--out", default=DEFAULT_SCORECARD)
    args = p.parse_args()

    rows = load_dataset(args.dataset)
    if args.limit:
        rows = rows[: args.limit]

    graph = build_graph()
    results: list[dict] = []
    for i, row in enumerate(rows, 1):
        log.info("[%d/%d] %s :: %s", i, len(rows), row["id"], row["prompt"][:80])
        t0 = time.time()
        try:
            state = asyncio.run(
                graph.ainvoke(
                    {
                        "user_message": row["prompt"],
                        "messages": [],
                        "denomination_pref": row.get("denomination_pref"),
                        "audit": [],
                    }
                )
            )
        except Exception as exc:
            log.exception("graph failed on %s", row["id"])
            state = {"final_content": f"[error: {exc}]", "safety_flags": {"refused": False}}
        latency = int((time.time() - t0) * 1000)
        judge = judge_row(row, state)
        results.append(
            {
                **row,
                "response": state.get("final_content", ""),
                "citations_verified": (state.get("safety_flags") or {}).get("citations_verified"),
                "intent": state.get("intent"),
                "image_url": state.get("image_url"),
                "latency_ms": latency,
                "judge": judge.to_dict(),
            }
        )

    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(summarize(results))
    raw_out = args.out.replace(".md", ".jsonl")
    with open(raw_out, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    log.info("scorecard written to %s and raw results to %s", args.out, raw_out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
