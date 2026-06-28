"""Code-generation quality + consistency eval.

Runs a small set of representative coding tasks through the sandbox builder with
review-and-repair ON, scoring the diff BEFORE repair (the raw single generation)
and AFTER repair with a judge rubric. One task is run 3x to quantify run-to-run
consistency. Reports the repair lift and the consistency spread.

Run in-container:  docker exec odysseus-odysseus-1 python /app/scripts/eval_codegen.py
"""

import asyncio
import json
import re
import statistics

from src.workspace_request_executor import execute_sandbox_coding_request, _read_patch_text, ROOT
from src.llm_core import llm_call_async

ENDPOINT = "http://host.docker.internal:11434/v1/chat/completions"
MODEL = "qwen3-coder:30b"
MAX_ROUNDS = 8

TASKS = [
    {"id": "duration", "prompt": "Create src/duration.py with parse_duration(s) that parses strings like '1h30m', '45s', '2h' into total seconds (int), supporting h/m/s units in any combination. Raise ValueError on invalid input such as '', 'abc', or '1x'."},
    {"id": "lru", "prompt": "Create src/lru.py with an LRUCache class: __init__(capacity), get(key) returns the value or None, put(key, value). Evict the least-recently-used entry when over capacity. get and put should be O(1)."},
    {"id": "anagrams", "prompt": "Create src/anagrams.py with group_anagrams(words) returning a list of lists that groups words which are anagrams of each other. Handle empty input and treat words case-insensitively."},
    {"id": "flatten", "prompt": "Create src/flatten.py with flatten(nested) that flattens an arbitrarily-nested list of integers into a single flat list, preserving order. Handle empty lists and already-flat lists."},
]
CONSISTENCY_TASK = TASKS[0]
CONSISTENCY_REPEATS = 2  # plus the first run = 3 total


async def score(task_prompt, diff):
    if not diff:
        return 0.0
    p = (f"TASK:\n{task_prompt}\n\nSOLUTION DIFF:\n{diff}\n\n"
         "Score this solution 1-5 on correctness + completeness + edge-case handling for the task "
         "(5 = correct, complete, handles edges; 3 = happy path works but misses edges; 1 = wrong/incomplete). "
         'Reply with ONLY JSON: {"score": N, "reason": "..."}.')
    try:
        out = await llm_call_async(ENDPOINT, MODEL, [{"role": "user", "content": p}],
                                   temperature=0.0, max_tokens=200, headers={})
        m = re.search(r"\{.*\}", out or "", re.S)
        if m:
            return float(json.loads(m.group(0)).get("score", 0))
        m2 = re.search(r"[1-5]", out or "")
        return float(m2.group(0)) if m2 else 0.0
    except Exception:
        return 0.0


async def run_one(task, idx):
    res = await execute_sandbox_coding_request(
        tracking_id=f"eval_{task['id']}_{idx}", prompt=task["prompt"], owner="admin",
        session_id=None, endpoint_url=ENDPOINT, model=MODEL, headers={},
        max_rounds=MAX_ROUNDS, temperature=0.6, review_repair=True,
    )
    applied = bool(res.get("review_repair_applied"))
    post_diff = _read_patch_text(ROOT, res.get("patch_file"), 4000) if res.get("patch_file") else ""
    pre_diff = res.get("pre_repair_diff") if applied else post_diff
    pre_checks = res.get("pre_repair_checks_status") if applied else res.get("checks_status")
    pre_score = await score(task["prompt"], pre_diff)
    post_score = await score(task["prompt"], post_diff)
    return {
        "task": task["id"], "repair_applied": applied,
        "pre_checks": pre_checks, "post_checks": res.get("checks_status"),
        "pre_score": pre_score, "post_score": post_score,
        "issues": (res.get("review_issues") or "")[:100],
    }


async def main():
    results = []
    for t in TASKS:
        results.append(await run_one(t, 0))
    cons = [results[0]["pre_score"]]
    for i in range(1, CONSISTENCY_REPEATS + 1):
        r = await run_one(CONSISTENCY_TASK, i)
        r["task"] = f"{CONSISTENCY_TASK['id']}_rep{i}"
        results.append(r)
        cons.append(r["pre_score"])

    pre = [r["pre_score"] for r in results]
    post = [r["post_score"] for r in results]
    summary = {
        "per_task": results,
        "mean_pre_score": round(statistics.mean(pre), 2),
        "mean_post_score": round(statistics.mean(post), 2),
        "pre_pass_rate": round(sum("PASS" in str(r["pre_checks"]) for r in results) / len(results), 2),
        "post_pass_rate": round(sum("PASS" in str(r["post_checks"]) for r in results) / len(results), 2),
        "repairs_applied": sum(r["repair_applied"] for r in results),
        "consistency_task": CONSISTENCY_TASK["id"],
        "consistency_pre_scores": cons,
        "consistency_stdev": round(statistics.pstdev(cons), 3),
    }
    print("EVAL " + json.dumps(summary))


asyncio.run(main())
