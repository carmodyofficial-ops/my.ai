from __future__ import annotations

import argparse
import inspect
import json
import sys
from pathlib import Path
from typing import Any

from src.workspace_patch_approval import DEFAULT_APPROVAL_PHRASE, apply_reviewed_patch
from src.workspace_patch_review import review_patch


def _json_default(value: Any) -> str:
    return str(value)


def _write_json(payload: dict[str, Any], report: str | Path | None = None) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True, default=_json_default)
    print(text)
    if report:
        report_path = Path(report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(text + "\n")


def _call_supported(
    fn: Any,
    *,
    patch_file: str | Path,
    root: str | Path,
    allowed_prefixes: list[str] | None = None,
    approval_phrase: str | None = None,
    required_approval_phrase: str | None = None,
) -> dict[str, Any]:
    sig = inspect.signature(fn)
    kwargs: dict[str, Any] = {}

    for name, param in sig.parameters.items():
        lname = name.lower()

        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue

        if ("patch" in lname and "path" in lname) or lname in {"patch", "patch_file", "diff", "diff_path"}:
            kwargs[name] = patch_file
        elif lname in {"root", "repo_root", "repository", "repo", "cwd", "worktree", "worktree_path"}:
            kwargs[name] = root
        elif "allowed" in lname and "prefix" in lname:
            kwargs[name] = allowed_prefixes
        elif "prefix" in lname and "allowed" in lname:
            kwargs[name] = allowed_prefixes
        elif lname == "approval_phrase":
            kwargs[name] = approval_phrase
        elif lname == "required_approval_phrase":
            kwargs[name] = required_approval_phrase
        elif "approval" in lname or "phrase" in lname:
            if "required" in lname or "expected" in lname:
                kwargs[name] = required_approval_phrase
            else:
                kwargs[name] = approval_phrase
        elif param.default is not inspect._empty:
            continue
        else:
            raise TypeError(f"Cannot safely supply required parameter {name!r} for {fn.__name__}")

    result = fn(**kwargs)
    if isinstance(result, dict):
        return result
    if hasattr(result, "__dict__"):
        return dict(result.__dict__)
    return {"raw_result_repr": repr(result)}


def review_command(args: argparse.Namespace) -> int:
    result = _call_supported(
        review_patch,
        patch_file=args.patch_file,
        root=args.root,
        allowed_prefixes=args.allowed_prefixes,
    )
    _write_json(result, args.report)

    return 0 if result.get("status") == "PASS_PATCH_REVIEW" else 2


def apply_command(args: argparse.Namespace) -> int:
    result = _call_supported(
        apply_reviewed_patch,
        patch_file=args.patch_file,
        root=args.root,
        allowed_prefixes=args.allowed_prefixes,
        approval_phrase=args.approval,
        required_approval_phrase=args.required_approval,
    )
    _write_json(result, args.report)

    return 0 if result.get("status") == "PASS_REVIEWED_PATCH_APPLIED" else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="workspace-patch",
        description="Review and explicitly approve safe workspace patches.",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    review = sub.add_parser("review", help="Review a patch without applying it.")
    review.add_argument("patch_file")
    review.add_argument("--root", default=".")
    review.add_argument("--allowed-prefix", action="append", dest="allowed_prefixes")
    review.add_argument("--report")
    review.set_defaults(func=review_command)

    apply = sub.add_parser("apply", help="Apply a reviewed patch only with an exact approval phrase.")
    apply.add_argument("patch_file")
    apply.add_argument("--root", default=".")
    apply.add_argument("--allowed-prefix", action="append", dest="allowed_prefixes")
    apply.add_argument("--approval", required=True)
    apply.add_argument("--required-approval", default=DEFAULT_APPROVAL_PHRASE)
    apply.add_argument("--report")
    apply.set_defaults(func=apply_command)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
