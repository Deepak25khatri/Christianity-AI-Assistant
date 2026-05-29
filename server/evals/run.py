"""Run the eval dataset against the LangGraph and produce a markdown scorecard.

Usage:
    python -m evals.run
    python -m evals.run --limit 10
    python -m evals.run --out /data/scorecard.md
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from collections import Counter, defaultdict
from typing import Any, Dict, List

from rag.graph import build_graph

log = logging.getLogger("evals.run")

HERE = os.path.dirname(__file__)
DEFAULT_DATASET = os.path.join(HERE, "dataset.jsonl")


def load_dataset(path: str) -> List[Dict[str, Any]]:
    rows: list[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _judge(row: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    """Heuristic per-row pass/fail based on the row's `expect` block."""
    expect = row.get("expect") or {}
    content = (result.get("final_content") or "").lower()
    safety = result.get("safety_flags") or {}
    refused = bool(safety.get("refused"))
    citations = result.get("citations") or []
    cited_refs = {c["ref"] for c in citations if c.get("exists")}

    notes: list[str] = []
    passed = True

    if expect.get("must_refuse") and not refused:
        passed = False
        notes.append("expected refusal but assistant answered")
    if expect.get("must_not_refuse") and refused:
        passed = False
        notes.append("unexpected refusal")
    for ref in expect.get("must_cite", []) or []:
        if not any(ref.lower() in c.lower() for c in cited_refs):
            passed = False
            notes.append(f"missing citation {ref}")
    if expect.get("must_cite_any"):
        if not any(any(opt.lower() in c.lower() for c in cited_refs)
                   for opt in expect["must_cite_any"]):
            passed = False
            notes.append(f"missing any of {expect['must_cite_any']}")
    for ref in expect.get("must_not_cite_existing", []) or []:
        if any(ref.lower() in c.lower() for c in citations
               if isinstance(c, dict) and c.get("exists")):
            passed = False
            notes.append(f"hallucinated citation {ref} marked as existing")
    if expect.get("should_acknowledge_no_such_book") or expect.get("should_acknowledge_no_such_verse"):
        if not any(k in content for k in ("no such", "does not exist", "isn't a", "not a book",
                                          "not in the bible", "couldn't find", "could not find",
                                          "doesn't appear")):
            notes.append("did not explicitly acknowledge fake verse (soft)")
    if expect.get("intent"):
        if (result.get("intent") or "") != expect["intent"]:
            notes.append(f"intent={result.get('intent')} expected {expect['intent']}")

    return {"passed": passed, "notes": notes, "refused": refused,
            "intent": result.get("intent"), "citations_verified": safety.get("citations_verified")}


def _summarize(rows: List[Dict[str, Any]]) -> str:
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_cat[r["category"]].append(r)
    lines = ["# Christianity AI - Eval Scorecard\n"]
    total_pass = sum(1 for r in rows if r["judge"]["passed"])
    lines.append(f"**Overall**: {total_pass}/{len(rows)} passed "
                 f"({(100*total_pass/len(rows)):.1f}%)\n")
    lines.append("## Per-category results\n")
    for cat, items in sorted(by_cat.items()):
        passed = sum(1 for r in items if r["judge"]["passed"])
        lines.append(f"- **{cat}**: {passed}/{len(items)} ({(100*passed/len(items)):.0f}%)")
    lines.append("\n## Failures\n")
    failures = [r for r in rows if not r["judge"]["passed"]]
    if not failures:
        lines.append("None - all evals passed.")
    else:
        for r in failures:
            lines.append(f"### {r['id']} ({r['category']})")
            lines.append(f"- Prompt: `{r['prompt']}`")
            lines.append(f"- Notes: {r['judge']['notes']}")
            lines.append(f"- Refused: {r['judge']['refused']}")
            lines.append(f"- Citations verified: {r['judge']['citations_verified']}")
            preview = (r["response"] or "")[:300].replace("\n", " ")
            lines.append(f"- Response preview: {preview}\n")
    lines.append("\n## Notes (soft signals)\n")
    soft = Counter()
    for r in rows:
        for n in r["judge"]["notes"]:
            if "soft" in n.lower():
                soft[n] += 1
    for n, c in soft.most_common():
        lines.append(f"- {n}: {c}")
    return "\n".join(lines) + "\n"


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s :: %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", default=DEFAULT_DATASET)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--out", default="/data/scorecard.md")
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
            state = asyncio.run(graph.ainvoke({
                "user_message": row["prompt"],
                "messages": [],
                "denomination_pref": row.get("denomination_pref"),
                "audit": [],
            }))
        except Exception as exc:
            log.exception("graph failed on %s", row["id"])
            state = {"final_content": f"[error: {exc}]", "safety_flags": {"refused": False}}
        latency = int((time.time() - t0) * 1000)
        judge = _judge(row, state)
        results.append({
            **row,
            "response": state.get("final_content", ""),
            "citations_verified": (state.get("safety_flags") or {}).get("citations_verified"),
            "intent": state.get("intent"),
            "latency_ms": latency,
            "judge": judge,
        })

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(_summarize(results))
    raw_out = args.out.replace(".md", ".jsonl")
    with open(raw_out, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    log.info("scorecard written to %s and raw results to %s", args.out, raw_out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
