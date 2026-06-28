"""Objective code-gen eval: real unit tests, no judge.

For each task the sandbox builder generates a single new file; we extract that
file from the produced patch, import it, and run a hidden assertion suite.
Score = fraction of assertions passed (objective). With review-repair ON we score
the diff BEFORE repair (pre_repair_diff) and the final kept diff, so the lift is
measured against ground truth, not a self-grading rubric. One task runs 3x for
run-to-run consistency.

Run:  docker exec -i odysseus-odysseus-1 python - < scripts/eval_codegen_v2.py
"""

import asyncio
import importlib.util
import json
import statistics
import tempfile

from src.workspace_request_executor import execute_sandbox_coding_request, _read_patch_text, ROOT

ENDPOINT = "http://host.docker.internal:11434/v1/chat/completions"
MODEL = "qwen3-coder:30b"
MAX_ROUNDS = 8


def _extract_new_file(diff: str) -> str:
    """Reconstruct the added file body from a unified diff (all '+' lines)."""
    out = []
    for line in (diff or "").splitlines():
        if line.startswith("+++") or line.startswith("+ ++"):
            continue
        if line.startswith("+"):
            out.append(line[1:])
    return "\n".join(out)


def _load(diff: str, idx):
    src = _extract_new_file(diff)
    if not src.strip():
        return None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=f"_{idx}.py", delete=False) as f:
            f.write(src)
            path = f.name
        spec = importlib.util.spec_from_file_location(f"evalmod_{idx}", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _ck(checks):
    """checks: list of (label, callable_returning_bool). Returns (passed, total)."""
    p = 0
    for _, fn in checks:
        try:
            if fn():
                p += 1
        except Exception:
            pass
    return p, len(checks)


def check_duration(m):
    f = getattr(m, "parse_duration", None)
    if not f:
        return 0, 1
    raises = lambda x: (_raises(f, x))
    cs = [("1h30m", lambda: f("1h30m") == 5400), ("45s", lambda: f("45s") == 45),
          ("2h", lambda: f("2h") == 7200), ("1h1m1s", lambda: f("1h1m1s") == 3661),
          ("bad_empty", lambda: raises("")), ("bad_abc", lambda: raises("abc")),
          ("bad_1x", lambda: raises("1x"))]
    return _ck(cs)


def check_lru(m):
    C = getattr(m, "LRUCache", None)
    if not C:
        return 0, 1

    def scenario():
        c = C(2); c.put(1, 1); c.put(2, 2)
        assert c.get(1) == 1
        c.put(3, 3)  # evicts 2 (LRU)
        assert c.get(2) is None
        assert c.get(3) == 3
        c.put(4, 4)  # evicts 1
        assert c.get(1) is None
        assert c.get(4) == 4
        return True
    return _ck([("scenario", scenario)])


def check_anagrams(m):
    f = getattr(m, "group_anagrams", None)
    if not f:
        return 0, 1

    def grp():
        r = f(["eat", "tea", "tan", "ate", "nat", "bat"])
        norm = sorted(sorted(w.lower() for w in g) for g in r)
        return norm == sorted([["ate", "eat", "tea"], ["nat", "tan"], ["bat"]])
    return _ck([("group", grp), ("empty", lambda: f([]) == [])])


def check_flatten(m):
    f = getattr(m, "flatten", None)
    if not f:
        return 0, 1
    cs = [("nested", lambda: f([1, [2, [3, 4]], 5]) == [1, 2, 3, 4, 5]),
          ("empty", lambda: f([]) == []),
          ("inner_empty", lambda: f([[], [1]]) == [1])]
    return _ck(cs)


def check_roman(m):
    f = getattr(m, "int_to_roman", None)
    if not f:
        return 0, 1
    cs = [("4", lambda: f(4) == "IV"), ("9", lambda: f(9) == "IX"),
          ("58", lambda: f(58) == "LVIII"), ("1994", lambda: f(1994) == "MCMXCIV"),
          ("3", lambda: f(3) == "III")]
    return _ck(cs)


def check_rpn(m):
    f = getattr(m, "eval_rpn", None)
    if not f:
        return 0, 1
    cs = [("a", lambda: f(["2", "1", "+", "3", "*"]) == 9),
          ("b", lambda: f(["4", "13", "5", "/", "+"]) == 6)]
    return _ck(cs)


def _raises(f, x):
    try:
        f(x)
        return False
    except Exception:
        return True


TASKS = [
    {"id": "duration", "check": check_duration,
     "prompt": "Create src/duration.py with parse_duration(s) that parses strings like '1h30m', '45s', '2h' into total seconds (int), supporting h/m/s units in any combination. Raise ValueError on invalid input such as '', 'abc', or '1x'."},
    {"id": "lru", "check": check_lru,
     "prompt": "Create src/lru.py with an LRUCache class: __init__(capacity), get(key) returns the value or None, put(key, value). Evict the least-recently-used entry when over capacity. get/put should be O(1)."},
    {"id": "anagrams", "check": check_anagrams,
     "prompt": "Create src/anagrams.py with group_anagrams(words) returning a list of lists grouping words that are anagrams of each other. Handle empty input; treat words case-insensitively."},
    {"id": "flatten", "check": check_flatten,
     "prompt": "Create src/flatten.py with flatten(nested) that flattens an arbitrarily-nested list of integers into a single flat list, preserving order. Handle empty and already-flat lists."},
    {"id": "roman", "check": check_roman,
     "prompt": "Create src/roman.py with int_to_roman(n) that converts an integer 1..3999 to its Roman numeral string (e.g. 4 -> 'IV', 1994 -> 'MCMXCIV')."},
    {"id": "rpn", "check": check_rpn,
     "prompt": "Create src/rpn.py with eval_rpn(tokens) that evaluates a list of Reverse Polish Notation tokens (operators + - * /, integer division truncating toward zero) and returns the integer result."},
]
CONSISTENCY_TASK = TASKS[0]
CONSISTENCY_REPEATS = 2


async def run_one(task, idx):
    res = await execute_sandbox_coding_request(
        tracking_id=f"evalv2_{task['id']}_{idx}", prompt=task["prompt"], owner="admin",
        session_id=None, endpoint_url=ENDPOINT, model=MODEL, headers={},
        max_rounds=MAX_ROUNDS, temperature=0.6, review_repair=True,
    )
    applied = bool(res.get("review_repair_applied"))
    final_diff = _read_patch_text(ROOT, res.get("patch_file"), 8000) if res.get("patch_file") else ""
    pre_diff = res.get("pre_repair_diff") if applied else final_diff
    pre_mod = _load(pre_diff, f"{task['id']}_{idx}_pre")
    post_mod = _load(final_diff, f"{task['id']}_{idx}_post")
    pre_p, pre_t = task["check"](pre_mod) if pre_mod else (0, 1)
    post_p, post_t = task["check"](post_mod) if post_mod else (0, 1)
    return {
        "task": task["id"], "repair_applied": applied,
        "pre_score": round(pre_p / pre_t, 3), "post_score": round(post_p / post_t, 3),
        "pre": f"{pre_p}/{pre_t}", "post": f"{post_p}/{post_t}",
    }


async def main():
    results = []
    for t in TASKS:
        results.append(await run_one(t, 0))
    cons = [results[0]["post_score"]]
    for i in range(1, CONSISTENCY_REPEATS + 1):
        r = await run_one(CONSISTENCY_TASK, i)
        r["task"] = f"{CONSISTENCY_TASK['id']}_rep{i}"
        results.append(r)
        cons.append(r["post_score"])

    pre = [r["pre_score"] for r in results]
    post = [r["post_score"] for r in results]
    summary = {
        "per_task": results,
        "mean_pre_score": round(statistics.mean(pre), 3),
        "mean_post_score": round(statistics.mean(post), 3),
        "fully_solved_pre": sum(r["pre_score"] == 1.0 for r in results),
        "fully_solved_post": sum(r["post_score"] == 1.0 for r in results),
        "n": len(results),
        "consistency_post_scores": cons,
        "consistency_stdev": round(statistics.pstdev(cons), 3),
    }
    print("EVALV2 " + json.dumps(summary))


asyncio.run(main())
