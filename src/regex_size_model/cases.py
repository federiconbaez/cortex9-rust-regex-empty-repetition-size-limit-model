"""Fixture loading and the repetition-count progression."""
import json
from pathlib import Path

from .compiler import DEFAULT_SIZE_LIMIT, VERSIONS, compile_pattern


def load(path) -> list:
    return json.loads(Path(path).read_text())["cases"]


def run_case(c: dict) -> dict:
    return {v: compile_pattern(c["pattern"], v, c["size_limit"], c["budget"]).as_dict() for v in VERSIONS}


PROGRESSION_N = (10, 100, 1000, 10_000, 100_000, 1_000_000, 4_294_967_295)
PROGRESSION_BUDGET = 3_000_000


def progression():
    for n in PROGRESSION_N:
        pat = "(?:){%d}" % n
        yield n, {v: compile_pattern(pat, v, DEFAULT_SIZE_LIMIT, PROGRESSION_BUDGET) for v in VERSIONS}
