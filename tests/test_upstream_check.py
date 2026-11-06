"""upstream_check.py must FAIL on empty, truncated, extra or wrong tool output
and must never write a summary from partial coverage (fake tools, no cargo)."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
import upstream_check as U  # noqa: E402
from regex_size_model import hir as H  # noqa: E402
from regex_size_model.cases import load, run_case  # noqa: E402

CASES = load(ROOT / "fixtures/cases.json")
_BY_NAME = {c["name"]: run_case(c) for c in CASES}
MODEL = {c["pattern"] + "\t" + str(c["size_limit"]): _BY_NAME[c["name"]] for c in CASES}


def setUpModule():
    # the model is deterministic; reuse its results instead of recomputing per run
    global _orig
    _orig, U.run_case = U.run_case, lambda c: _BY_NAME[c["name"]]


def tearDownModule():
    U.run_case = _orig


def honest(name, stdin):
    """Answers exactly what the model says (stands in for the real crates)."""
    rows = []
    for line in stdin.splitlines():
        if name == "hir_dump":
            rows.append([line, U.sexp(H.parse(line))])
        else:
            ver = "pre" if name == "compile_1_5_4" else "fix"
            p, lim = line.split("\t")
            rows.append([p, lim, MODEL[line][ver]["status"]])
    return rows


def mutate(target, f):
    def tool(name, stdin):
        rows = honest(name, stdin)
        return f(rows) if name == target else rows
    return tool


class UpstreamValidation(unittest.TestCase):
    def run_main(self, tool):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "o"
            try:
                return U.main(out, tool=tool), sorted(p.name for p in out.glob("*"))
            except U.UpstreamError:
                self.assertFalse(out.exists() and any(out.iterdir()), "files written on failure")
                raise

    def test_honest_tools_pass_with_full_coverage(self):
        rc, files = self.run_main(honest)
        self.assertEqual((rc, files), (0, ["compile.tsv", "hir.tsv", "summary.json"]))

    def check_fails(self, tool):
        with self.assertRaises(U.UpstreamError):
            self.run_main(tool)

    def test_hir_empty_truncated_extra_fail(self):
        self.check_fails(mutate("hir_dump", lambda r: []))
        self.check_fails(mutate("hir_dump", lambda r: r[:-1]))
        self.check_fails(mutate("hir_dump", lambda r: r + [r[0]]))

    def test_hir_wrong_echo_or_width_fails(self):
        self.check_fails(mutate("hir_dump", lambda r: [["zzz", r[0][1]]] + r[1:]))
        self.check_fails(mutate("hir_dump", lambda r: [r[0][:1]] + r[1:]))

    def test_compile_empty_truncated_extra_fail(self):
        for crate in ("compile_1_5_4", "compile_1_5_5"):
            self.check_fails(mutate(crate, lambda r: []))
            self.check_fails(mutate(crate, lambda r: r[:-1]))
            self.check_fails(mutate(crate, lambda r: r + [r[0]]))

    def test_compile_wrong_pattern_limit_status_fail(self):
        crate = "compile_1_5_5"
        self.check_fails(mutate(crate, lambda r: [["b", r[0][1], r[0][2]]] + r[1:]))
        self.check_fails(mutate(crate, lambda r: [[r[0][0], "1", r[0][2]]] + r[1:]))
        self.check_fails(mutate(crate, lambda r: [[r[0][0], r[0][1], "ERR Syntax"]] + r[1:]))

    def test_mismatch_is_reported_not_hidden(self):
        flip = {"OK": "COMPILED_TOO_BIG", "COMPILED_TOO_BIG": "OK"}
        rc, _ = self.run_main(mutate("compile_1_5_5", lambda r: [[r[0][0], r[0][1], flip[r[0][2]]]] + r[1:]))
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
