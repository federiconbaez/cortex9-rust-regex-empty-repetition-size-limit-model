"""CLI: compile-size accounting for one pattern under pre and fix."""
import argparse
import json
import sys

from .compiler import DEFAULT_BUDGET, DEFAULT_SIZE_LIMIT, VERSIONS, compile_pattern
from .hir import ParseError


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="regex_size_model",
                                 description="Offline model of regex 1.5.4 size accounting (budgeted).")
    ap.add_argument("pattern")
    ap.add_argument("--size-limit", type=int, default=DEFAULT_SIZE_LIMIT)
    ap.add_argument("--budget", type=int, default=DEFAULT_BUDGET)
    ap.add_argument("--version", choices=VERSIONS + ("both",), default="both")
    a = ap.parse_args(argv)
    try:
        for v in (VERSIONS if a.version == "both" else (a.version,)):
            print(json.dumps(compile_pattern(a.pattern, v, a.size_limit, a.budget).as_dict()))
    except ParseError as e:
        print(f"unsupported pattern: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
